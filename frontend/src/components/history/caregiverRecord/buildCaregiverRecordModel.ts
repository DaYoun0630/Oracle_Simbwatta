import { TREND_RANGE_OPTIONS, type TrendRangeKey } from "@/composables/useTrendRange";
import type {
  CaregiverRecordPageModel,
  DailyTrendLevel,
  DailyTrendPoint,
  EvidenceLog,
  ObservationDomain,
  ObservationItem,
} from "./types";

const DOMAIN_ORDER: ObservationDomain[] = ["training", "speech", "participation"];

const pad2 = (value: number) => String(value).padStart(2, "0");

const toISODate = (date: Date) =>
  `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;

const getDaysForRange = (range: TrendRangeKey) =>
  TREND_RANGE_OPTIONS.find((option) => option.key === range)?.days ?? 7;

const buildDateRangeLabel = (dates: string[]) => {
  if (!dates.length) return "-";
  const first = dates[0];
  const last = dates[dates.length - 1];
  return `${first} ~ ${last}`;
};

const SIX_MONTH_DAYS = 182;

const resolveScenarioLevel = (index: number): DailyTrendLevel => {
  const stablePhaseEnd = 122;
  const slightDeclineEnd = 152;
  const oscillationEnd = 175;
  const last7Pattern: DailyTrendLevel[] = [
    "stable",
    "decline",
    "stable",
    "missing",
    "decline",
    "stable",
    "decline",
  ];

  if (index < stablePhaseEnd) {
    return index % 17 === 0 ? "change" : "stable";
  }

  if (index < slightDeclineEnd) {
    if (index % 7 === 0) return "decline";
    return "change";
  }

  if (index < oscillationEnd) {
    return index % 2 === 0 ? "stable" : "decline";
  }

  return last7Pattern[index - oscillationEnd] ?? "decline";
};

const buildDailyTrendPoints = (days: number): DailyTrendPoint[] => {
  const points: DailyTrendPoint[] = [];
  const endDate = new Date();
  const startIndex = Math.max(0, SIX_MONTH_DAYS - days);

  for (let i = days - 1; i >= 0; i -= 1) {
    const date = new Date(endDate);
    date.setDate(endDate.getDate() - i);
    const scenarioIndex = startIndex + (days - 1 - i);
    const level = resolveScenarioLevel(scenarioIndex);
    points.push({
      date: toISODate(date),
      level,
      flags: level === "decline" && scenarioIndex >= 122 ? ["ANOMALY"] : [],
      metrics: {
        interruptions: level === "decline" ? 4 : level === "change" ? 2 : level === "missing" ? 0 : 1,
        responseDelayPercent: level === "decline" ? 21 : level === "change" ? 11 : level === "missing" ? 0 : 4,
        participationGap: level === "missing",
      },
    });
  }

  return points;
};

const buildObservationItems = (logs: EvidenceLog[]): ObservationItem[] => {
  const byDomain: Record<ObservationDomain, EvidenceLog[]> = {
    training: [],
    speech: [],
    participation: [],
  };

  logs.forEach((log, index) => {
    const domain = DOMAIN_ORDER[index % DOMAIN_ORDER.length];
    byDomain[domain].push(log);
  });

  return [
    {
      domain: "training",
      severity: "주의",
      title: "훈련 몰입도 편차 관찰",
      deltaMetrics: "지난 7일 중단 3회 (이전 7일 대비 +1)",
      evidenceLogs: byDomain.training,
      actions: ["짧은 세션(10~15분)으로 분할하기", "피로도가 낮은 오전 시간으로 일정 이동"],
    },
    {
      domain: "speech",
      severity: "가벼움",
      title: "발화 반응 지연 경향",
      deltaMetrics: "평균 반응 지연 +8%",
      evidenceLogs: byDomain.speech,
      actions: ["질문 간격 3~5초 유지", "답변 전 힌트 문장 1개 제공"],
    },
    {
      domain: "participation",
      severity: "주의",
      title: "참여 리듬 불균형",
      deltaMetrics: "저녁 시간 미참여 2회",
      evidenceLogs: byDomain.participation,
      actions: ["저녁 루틴에 고정 알림 추가", "보호자 동행 체크인 1회 추가"],
    },
  ];
};

export const buildCaregiverRecordModel = (range: TrendRangeKey): CaregiverRecordPageModel => {
  const days = getDaysForRange(range);
  const dailyTrendPoints = buildDailyTrendPoints(days);

  const rawLogs: EvidenceLog[] = dailyTrendPoints.map((point) => ({
    date: point.date,
    detail:
      point.level === "decline"
        ? "응답 지연과 중단이 함께 증가"
        : point.level === "missing"
          ? "참여 기록이 없어 추세를 측정하지 못함"
        : point.level === "change"
          ? "반응 속도 변동이 관찰됨"
          : "평균 범위 내 활동 유지",
  }));

  const declineCount = dailyTrendPoints.filter((point) => point.level === "decline").length;
  const changeCount = dailyTrendPoints.filter((point) => point.level === "change").length;
  const status = declineCount > 0 ? "저하" : changeCount > 1 ? "변화" : "안정";

  return {
    range,
    periodSummary: {
      status,
      evidenceMetrics: `중단 ${declineCount + changeCount}회, 반응지연 평균 +${Math.max(
        6,
        4 + changeCount * 3 + declineCount * 5
      )}%`,
      recommendedAction: "피로가 낮은 시간대로 훈련을 이동하고 짧은 세션으로 나누어 진행해 보세요.",
      dateRangeLabel: buildDateRangeLabel(dailyTrendPoints.map((point) => point.date)),
      quickStats: [
        `변화일 ${changeCount}일`,
        `저하일 ${declineCount}일`,
        `총 로그 ${rawLogs.length}건`,
      ],
      comparisonRows: [
        { label: "중단 횟수", current: `${declineCount + changeCount}회`, previous: `${changeCount}회` },
        { label: "반응 지연", current: `+${8 + declineCount * 4}%`, previous: "+6%" },
        { label: "미참여", current: "0일", previous: "1일" },
      ],
    },
    dailyTrendPoints,
    observationItems: buildObservationItems(rawLogs),
    notableChanges: [
      {
        domain: "speech",
        whenLabel: "24시간",
        title: "반응 속도 편차가 커졌습니다.",
        actionTip: "질문 수를 줄이고 한 문장씩 천천히 대화를 이어가세요.",
      },
      {
        domain: "training",
        whenLabel: "48시간",
        title: "훈련 중단 빈도가 증가했습니다.",
        actionTip: "훈련 시간을 15분 단위로 재구성해 피로 누적을 줄여보세요.",
      },
    ],
    rawLogs,
  };
};
