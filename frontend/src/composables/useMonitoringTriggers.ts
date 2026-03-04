import type { TrendRangeKey } from "@/composables/useTrendRange";
import type { BucketedTrendResult, TrendBucket } from "@/composables/useTrendBuckets";
import {
  ALERT_TAG_LABEL,
  ensureSafeAlertLine,
  sortAlertsByPriority,
  type AlertAxis,
  type CaregiverAlert,
} from "@/composables/caregiverAlertTypes";

const TRIGGER_COOLDOWN_MS = 24 * 60 * 60 * 1000;

const triggerStore = new Map<string, { createdAt: number; alert: CaregiverAlert }>();

const FALLBACK_TEXT: Record<AlertAxis, { title: string; action: string }> = {
  participation: {
    title: "최근에는 훈련 참여가 뜸한 흐름이 보여요.",
    action:
      "참여 흐름이 비면 생활 리듬 변화가 놓치기 쉬워요. 오늘은 짧게라도 한 번 이어가보세요. 부담 없이 시작해도 충분합니다.",
  },
  training: {
    title: "최근에는 수행 흐름이 갑자기 내려간 구간이 보여요.",
    action:
      "컨디션 영향을 겪는 시기일 수 있어요. 오늘은 쉬운 과제로 안정감을 먼저 잡아보세요. 짧게 진행해도 괜찮습니다.",
  },
  speech: {
    title: "최근에는 대화 흐름이 갑자기 끊기는 장면이 있었어요.",
    action:
      "응답 부담이 커진 시기일 수 있어요. 질문을 짧게 바꾸고 기다리는 시간을 조금 더 주세요. 천천히 이어가면 충분합니다.",
  },
};

const toDateOnly = (value: string) => new Date(`${value}T00:00:00`);

const rangeFromBuckets = (buckets: TrendBucket[]) => {
  if (!buckets.length) {
    const today = new Date();
    const dateText = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(
      today.getDate()
    ).padStart(2, "0")}`;
    return { startDate: dateText, endDate: dateText };
  }

  return {
    startDate: buckets[0].startDate,
    endDate: buckets[buckets.length - 1].endDate,
  };
};

const createTriggerAlert = (
  axis: AlertAxis,
  period: TrendRangeKey,
  startDate: string,
  endDate: string,
  titleLine: string,
  actionLine: string
): CaregiverAlert => ({
  id: `trigger-${axis}-${period}-${endDate}`,
  axis,
  tone: "caution",
  kind: "trigger",
  tagLabel: ALERT_TAG_LABEL[axis],
  titleLine: ensureSafeAlertLine(titleLine, FALLBACK_TEXT[axis].title),
  actionLine: ensureSafeAlertLine(actionLine, FALLBACK_TEXT[axis].action),
  startDate,
  endDate,
});

const buildTriggerCandidates = (
  period: TrendRangeKey,
  bucketedTrend: BucketedTrendResult,
  startDate: string,
  endDate: string
) => {
  const buckets = bucketedTrend.buckets;
  if (!buckets.length) return [] as CaregiverAlert[];

  const latest = buckets[buckets.length - 1];
  const previous = buckets.length > 1 ? buckets[buckets.length - 2] : null;
  const recent = buckets.slice(-3);
  const alerts: CaregiverAlert[] = [];

  const participationTriggered =
    latest.state === "missing" ||
    bucketedTrend.weeklyParticipation.triggered ||
    (latest.missingDays > 0 && previous?.missingDays === 0);

  if (participationTriggered) {
    alerts.push(
      createTriggerAlert(
        "participation",
        period,
        startDate,
        endDate,
        "최근에는 훈련 참여가 비는 구간이 감지됐어요.",
        "참여가 갑자기 끊기면 생활 리듬 변화를 놓치기 쉬워요. 오늘은 짧게라도 한 번 이어가보세요. 가볍게 확인해도 충분합니다."
      )
    );
  }

  const trainingTriggered =
    latest.state === "decline" &&
    (previous?.state !== "decline" || recent.filter((bucket) => bucket.state === "decline").length >= 2);

  if (trainingTriggered) {
    alerts.push(
      createTriggerAlert(
        "training",
        period,
        startDate,
        endDate,
        "최근에는 수행이 갑자기 어려워진 구간이 있었어요.",
        "일시적인 피로가 겹칠 수 있어요. 오늘은 난이도를 한 단계 낮춰 안정감을 먼저 만들어보세요. 작은 성공으로도 충분합니다."
      )
    );
  }

  const speechTriggered =
    latest.hasAnomaly ||
    (latest.state !== "stable" && previous?.state === "stable") ||
    recent.filter((bucket) => bucket.state !== "stable").length >= 2;

  if (speechTriggered) {
    alerts.push(
      createTriggerAlert(
        "speech",
        period,
        startDate,
        endDate,
        "최근에는 대화가 중간에 멈추는 순간이 있었어요.",
        "응답까지 여유가 필요한 시기일 수 있어요. 질문을 짧게 바꾸고 대답 시간을 조금 더 주세요. 천천히 맞춰가면 충분합니다."
      )
    );
  }

  return alerts;
};

export const buildMonitoringTriggers = (
  period: TrendRangeKey,
  bucketedTrend: BucketedTrendResult,
  nowDate: Date = new Date()
) => {
  const nowMs = nowDate.getTime();
  const range = rangeFromBuckets(bucketedTrend.buckets);
  const candidates = buildTriggerCandidates(period, bucketedTrend, range.startDate, range.endDate);

  for (const [key, entry] of triggerStore.entries()) {
    if (nowMs - entry.createdAt >= TRIGGER_COOLDOWN_MS) {
      triggerStore.delete(key);
    }
  }

  const activeAlerts: CaregiverAlert[] = [];

  candidates.forEach((candidate) => {
    const key = `axis:${candidate.axis}`;
    const cached = triggerStore.get(key);
    if (cached && nowMs - cached.createdAt < TRIGGER_COOLDOWN_MS) {
      activeAlerts.push(cached.alert);
      return;
    }
    triggerStore.set(key, { createdAt: nowMs, alert: candidate });
    activeAlerts.push(candidate);
  });

  return sortAlertsByPriority(activeAlerts);
};
