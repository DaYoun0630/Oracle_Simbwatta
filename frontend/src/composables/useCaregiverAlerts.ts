import type { TrendRangeKey } from "@/composables/useTrendRange";
import type { BucketedTrendResult, TrendBucket, TrendState } from "@/composables/useTrendBuckets";
import {
  ALERT_AXIS_PRIORITY,
  ALERT_KIND_LABEL,
  ALERT_TAG_LABEL,
  ALERT_TONE_LABEL,
  ensureSafeAlertLine,
  sortAlertsByPriority,
  type AlertAxis,
  type AlertKind,
  type CaregiverAlert,
} from "@/composables/caregiverAlertTypes";
import { buildMonitoringTriggers } from "@/composables/useMonitoringTriggers";

const toDateOnly = (value: string) => new Date(`${value}T00:00:00`);
const isLongPeriod = (period: TrendRangeKey) => period === "3m" || period === "6m";

const formatMonthDay = (isoDate: string) => {
  const date = toDateOnly(isoDate);
  if (Number.isNaN(date.getTime())) return isoDate;
  return `${date.getMonth() + 1}.${date.getDate()}`;
};

const resolveRange = (bucketedTrend: BucketedTrendResult) => {
  if (!bucketedTrend.buckets.length) {
    const today = new Date();
    const dateText = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(
      today.getDate()
    ).padStart(2, "0")}`;
    return { startDate: dateText, endDate: dateText };
  }

  return {
    startDate: bucketedTrend.buckets[0].startDate,
    endDate: bucketedTrend.buckets[bucketedTrend.buckets.length - 1].endDate,
  };
};

const splitByHalf = (buckets: TrendBucket[]) => {
  if (!buckets.length) return { early: [] as TrendBucket[], late: [] as TrendBucket[] };
  const pivot = Math.ceil(buckets.length / 2);
  return {
    early: buckets.slice(0, pivot),
    late: buckets.slice(pivot),
  };
};

const countMissingLike = (buckets: TrendBucket[]) =>
  buckets.filter((bucket) => bucket.state === "missing" || bucket.missingDays > 0).length;

const countNonStable = (buckets: TrendBucket[]) => buckets.filter((bucket) => bucket.state !== "stable").length;

const hasConsecutiveNonStable = (buckets: TrendBucket[], target: number) => {
  let streak = 0;
  for (const bucket of buckets) {
    if (bucket.state === "stable") {
      streak = 0;
      continue;
    }
    streak += 1;
    if (streak >= target) return true;
  }
  return false;
};

const FALLBACK_TEXT: Record<AlertAxis, { title: string; action: string }> = {
  participation: {
    title: "최근에는 훈련 참여 흐름이 흔들리는 구간이 보여요.",
    action:
      "생활 리듬이 달라지는 시기일 수 있어요. 오늘은 짧은 훈련으로 흐름을 이어가보세요. 부담 없이 진행해도 충분합니다.",
  },
  training: {
    title: "최근에는 수행 흐름이 고르지 않은 구간이 보여요.",
    action:
      "컨디션에 따라 결과가 달라질 수 있어요. 쉬운 과제로 안정감을 먼저 잡아보세요. 작은 진행으로도 충분합니다.",
  },
  speech: {
    title: "최근에는 대화 흐름이 끊기는 구간이 보여요.",
    action:
      "응답까지 시간이 필요한 시기일 수 있어요. 질문을 짧게 바꾸고 기다림을 조금 더 주세요. 천천히 맞춰가면 충분합니다.",
  },
};

const createAlert = (
  axis: AlertAxis,
  tone: CaregiverAlert["tone"],
  kind: AlertKind,
  period: TrendRangeKey,
  startDate: string,
  endDate: string,
  titleLine: string,
  actionLine: string
): CaregiverAlert => ({
  id: `${kind}-${axis}-${period}-${endDate}`,
  axis,
  tone,
  kind,
  tagLabel: ALERT_TAG_LABEL[axis],
  titleLine: ensureSafeAlertLine(titleLine, FALLBACK_TEXT[axis].title),
  actionLine: ensureSafeAlertLine(actionLine, FALLBACK_TEXT[axis].action),
  startDate,
  endDate,
});

const buildParticipationSummaryAlert = (
  period: TrendRangeKey,
  bucketedTrend: BucketedTrendResult,
  startDate: string,
  endDate: string
) => {
  const buckets = bucketedTrend.buckets;
  const { early, late } = splitByHalf(buckets);
  const earlyMissing = countMissingLike(early);
  const lateMissing = countMissingLike(late);

  if (bucketedTrend.weeklyParticipation.triggered || (lateMissing > 0 && lateMissing >= earlyMissing)) {
    return createAlert(
      "participation",
      "caution",
      "summary",
      period,
      startDate,
      endDate,
      "최근에는 훈련 참여가 뜸한 흐름이 보였어요.",
      "참여가 드물어지면 생활 리듬 변화를 놓치기 쉬워요. 오늘은 짧게라도 한 번 이어가보세요. 가볍게 시작해도 충분합니다."
    );
  }

  if (earlyMissing > 0 && lateMissing === 0) {
    return createAlert(
      "participation",
      "info",
      "summary",
      period,
      startDate,
      endDate,
      "최근에는 훈련을 다시 이어가는 흐름이 보였어요.",
      "루틴이 다시 붙는 시기일 수 있어요. 지금 페이스를 무리 없이 유지해보세요. 천천히 이어가도 충분합니다."
    );
  }

  return createAlert(
    "participation",
    "suggest",
    "summary",
    period,
    startDate,
    endDate,
    "훈련 참여가 들쑥날쑥한 구간이 있었어요.",
    "시간대를 한 번 정해두면 부담이 줄어들 수 있어요. 오늘은 같은 시간에 짧게 시작해보세요. 가볍게 해도 충분합니다."
  );
};

const buildTrainingSummaryAlert = (
  period: TrendRangeKey,
  bucketedTrend: BucketedTrendResult,
  startDate: string,
  endDate: string
) => {
  const metrics = bucketedTrend.metrics;
  const unstableCount = metrics.changeBuckets + metrics.declineBuckets;

  if (metrics.declineBuckets >= Math.max(1, Math.ceil(metrics.bucketCount * 0.35))) {
    return createAlert(
      "training",
      "caution",
      "summary",
      period,
      startDate,
      endDate,
      "최근에는 수행이 조금 어려웠던 구간이 있었어요.",
      "컨디션 영향이 겹친 시기일 수 있어요. 오늘은 난이도를 한 단계 낮춰 성공 경험을 먼저 만들어보세요. 천천히 진행해도 충분합니다."
    );
  }

  if (unstableCount > 0) {
    return createAlert(
      "training",
      "suggest",
      "summary",
      period,
      startDate,
      endDate,
      "날마다 수행 결과가 조금씩 달라진 흐름이 있었어요.",
      "리듬이 흔들리는 시기일 수 있어요. 짧고 쉬운 과제로 안정감을 먼저 잡아보세요. 작게 이어가도 충분합니다."
    );
  }

  return createAlert(
    "training",
    "info",
    "summary",
    period,
    startDate,
    endDate,
    "최근에는 수행 흐름이 비교적 안정적으로 이어졌어요.",
    "지금처럼 짧게 꾸준히 이어가면 안정감 유지에 도움이 돼요. 무리하지 않아도 충분합니다."
  );
};

const buildSpeechSummaryAlert = (
  period: TrendRangeKey,
  bucketedTrend: BucketedTrendResult,
  startDate: string,
  endDate: string
) => {
  const buckets = bucketedTrend.buckets;
  const recentBuckets = buckets.slice(-3);
  const recentNonStable = countNonStable(recentBuckets);
  const anomalyRecent = recentBuckets.filter((bucket) => bucket.hasAnomaly).length;

  const { early, late } = splitByHalf(buckets);
  const speechPersistent = hasConsecutiveNonStable(buckets, 2);
  const participationNoRecovery = countMissingLike(late) >= countMissingLike(early) && countMissingLike(late) > 0;

  if (isLongPeriod(period) && speechPersistent && participationNoRecovery && recentNonStable >= 1) {
    return createAlert(
      "speech",
      "consult",
      "summary",
      period,
      startDate,
      endDate,
      "대화 흐름의 정체가 이어지는 경향이 보였어요.",
      "생활 리듬과 대화 환경을 함께 점검해보면 도움이 될 수 있어요. 필요하면 전문가와 상의하는 선택지도 고려해보세요. 지금은 부담을 줄여 천천히 이어가면 충분합니다."
    );
  }

  if (recentNonStable >= 2 || anomalyRecent >= 1) {
    return createAlert(
      "speech",
      "caution",
      "summary",
      period,
      startDate,
      endDate,
      "대화가 중간에 멈추는 순간이 여러 번 있었어요.",
      "응답 부담이 커진 시기일 수 있어요. 질문을 짧게 하고 대답할 시간을 조금 더 주세요. 재촉하지 않고 이어가면 충분합니다."
    );
  }

  if (recentNonStable >= 1 || bucketedTrend.metrics.changeBuckets >= 1) {
    return createAlert(
      "speech",
      "suggest",
      "summary",
      period,
      startDate,
      endDate,
      "응답까지 여유가 필요한 순간이 있었어요.",
      "컨디션에 따라 반응 속도가 달라질 수 있어요. 선택형 질문으로 부담을 줄여보세요. 편안한 속도로 이어가면 충분합니다."
    );
  }

  return createAlert(
    "speech",
    "info",
    "summary",
    period,
    startDate,
    endDate,
    "대화가 비교적 자연스럽게 이어진 구간이 있었어요.",
    "이런 흐름을 유지하면 일상 대화가 한결 편해질 수 있어요. 지금 리듬을 가볍게 이어가도 충분합니다."
  );
};

export const buildSummaryAlerts = (period: TrendRangeKey, bucketedTrend: BucketedTrendResult) => {
  const range = resolveRange(bucketedTrend);

  return [
    buildParticipationSummaryAlert(period, bucketedTrend, range.startDate, range.endDate),
    buildTrainingSummaryAlert(period, bucketedTrend, range.startDate, range.endDate),
    buildSpeechSummaryAlert(period, bucketedTrend, range.startDate, range.endDate),
  ];
};

const selectPrimaryAlert = (summaryAlerts: CaregiverAlert[], monitoringAlerts: CaregiverAlert[]) => {
  const allAlerts = sortAlertsByPriority([...monitoringAlerts, ...summaryAlerts]);
  return allAlerts[0] ?? null;
};

const selectSecondaryAlerts = (summaryAlerts: CaregiverAlert[], primaryAlert: CaregiverAlert | null) => {
  const summaryByAxis = new Map(summaryAlerts.map((alert) => [alert.axis, alert]));
  const preferredAxes = ALERT_AXIS_PRIORITY.filter((axis) => axis !== primaryAlert?.axis);
  return preferredAxes.map((axis) => summaryByAxis.get(axis)).filter((alert): alert is CaregiverAlert => Boolean(alert));
};

export const formatSummaryRangeLabel = (startDate: string, endDate: string) =>
  `${formatMonthDay(startDate)} ~ ${formatMonthDay(endDate)} 평균 관찰`;

export const formatBucketRangeLabel = (bucket: TrendBucket) =>
  `${formatMonthDay(bucket.startDate)} ~ ${formatMonthDay(bucket.endDate)} 평균 관찰`;

const stateTextMap: Record<TrendState, string> = {
  stable: "안정 흐름이 이어진 구간",
  change: "변화가 감지된 구간",
  decline: "저하 흐름이 보인 구간",
  missing: "대화 참여가 확인되지 않은 구간",
};

export const getBucketStateText = (state: TrendState) => stateTextMap[state];

export const buildCaregiverAlertBundle = (
  period: TrendRangeKey,
  bucketedTrend: BucketedTrendResult,
  nowDate: Date = new Date()
) => {
  const summaryAlerts = buildSummaryAlerts(period, bucketedTrend);
  const monitoringAlerts = buildMonitoringTriggers(period, bucketedTrend, nowDate);
  const primaryAlert = selectPrimaryAlert(summaryAlerts, monitoringAlerts);
  const secondaryAlerts = selectSecondaryAlerts(summaryAlerts, primaryAlert).slice(0, 2);
  const range = resolveRange(bucketedTrend);

  return {
    summaryAlerts,
    monitoringAlerts,
    primaryAlert,
    secondaryAlerts,
    rangeStartDate: range.startDate,
    rangeEndDate: range.endDate,
    rangeLabel: formatSummaryRangeLabel(range.startDate, range.endDate),
  };
};

export const getAlertKindLabel = (kind: AlertKind) => ALERT_KIND_LABEL[kind];
export const getAlertToneLabel = (tone: CaregiverAlert["tone"]) => ALERT_TONE_LABEL[tone];
