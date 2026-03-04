import type { TrendPoint } from "@/domain/trend/contracts";
import { TREND_BUCKET_DAYS, type TrendRangeKey } from "@/composables/useTrendRange";

export type TrendState = "stable" | "change" | "decline" | "missing";
export type TrendTone = "stable" | "alert" | "down";

export interface TrendBucket {
  index: number;
  startDate: string;
  endDate: string;
  label: string;
  value: number | null;
  hasAnomaly: boolean;
  missingDays: number;
  points: TrendPoint[];
  state: TrendState;
}

export interface WeeklyParticipationAlert {
  triggered: boolean;
  missingDays: number;
  maxMissingStreak: number;
  message: string | null;
}

export interface TrendBucketMetrics {
  tone: TrendTone;
  statusLabel: string;
  summaryText: string;
  bucketCount: number;
  stableBuckets: number;
  changeBuckets: number;
  declineBuckets: number;
  missingBuckets: number;
  missingDays: number;
  signals: string[];
}

export interface BucketedTrendResult {
  buckets: TrendBucket[];
  values: Array<number | null>;
  labels: string[];
  dates: string[];
  states: TrendState[];
  highlights: number[];
  metrics: TrendBucketMetrics;
  weeklyParticipation: WeeklyParticipationAlert;
}

const STATE_LEVEL: Record<Exclude<TrendState, "missing">, number> = {
  stable: 2,
  change: 1,
  decline: 0,
};

const toDateOnly = (value: string) => new Date(`${value}T00:00:00`);
const round1 = (value: number) => Math.round(value * 10) / 10;

const sortByDate = (points: TrendPoint[]) =>
  [...points].sort((a, b) => toDateOnly(a.date).getTime() - toDateOnly(b.date).getTime());

const averageOf = (values: number[]) => {
  if (!values.length) return null;
  return round1(values.reduce((sum, value) => sum + value, 0) / values.length);
};

const formatMonthDay = (isoDate: string) => {
  const date = toDateOnly(isoDate);
  if (Number.isNaN(date.getTime())) return isoDate;
  return `${date.getMonth() + 1}.${date.getDate()}`;
};

const standardDeviation = (values: number[]) => {
  if (values.length < 2) return 0;
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  const variance =
    values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / Math.max(values.length - 1, 1);
  return Math.sqrt(variance);
};

const buildWeeklyParticipationAlert = (points: TrendPoint[]): WeeklyParticipationAlert => {
  const recentWeek = sortByDate(points).slice(-7);
  if (!recentWeek.length) {
    return {
      triggered: false,
      missingDays: 0,
      maxMissingStreak: 0,
      message: null,
    };
  }

  let missingDays = 0;
  let maxMissingStreak = 0;
  let streak = 0;

  recentWeek.forEach((point) => {
    const missing = point.sampleCount <= 0;
    if (missing) {
      missingDays += 1;
      streak += 1;
      maxMissingStreak = Math.max(maxMissingStreak, streak);
      return;
    }
    streak = 0;
  });

  const triggered = maxMissingStreak >= 3 || missingDays >= 4;
  if (!triggered) {
    return {
      triggered,
      missingDays,
      maxMissingStreak,
      message: null,
    };
  }

  if (maxMissingStreak >= 3) {
    return {
      triggered,
      missingDays,
      maxMissingStreak,
      message: "최근에는 연속으로 훈련 참여가 비는 흐름이 보여 확인이 필요해요.",
    };
  }

  return {
    triggered,
    missingDays,
    maxMissingStreak,
    message: "최근에는 참여 기록 공백이 이어져 생활 리듬 점검이 권장돼요.",
  };
};

const classifyBucketState = (
  bucket: Omit<TrendBucket, "state">,
  mean: number,
  std: number,
  previousValue: number | null
): TrendState => {
  if (bucket.value === null) return "missing";

  const value = bucket.value;
  const delta = previousValue === null ? 0 : value - previousValue;
  const strongDrop = Math.max(std * 0.7, 2.8);
  const softDrop = Math.max(std * 0.3, 1.4);

  if (value <= mean - strongDrop || delta <= -strongDrop) return "decline";
  if (value <= mean - softDrop || delta <= -softDrop || bucket.hasAnomaly || bucket.missingDays > 0) return "change";
  return "stable";
};

const buildMetrics = (buckets: TrendBucket[], weeklyParticipation: WeeklyParticipationAlert): TrendBucketMetrics => {
  const bucketCount = buckets.length;
  const stableBuckets = buckets.filter((bucket) => bucket.state === "stable").length;
  const changeBuckets = buckets.filter((bucket) => bucket.state === "change").length;
  const declineBuckets = buckets.filter((bucket) => bucket.state === "decline").length;
  const missingBuckets = buckets.filter((bucket) => bucket.state === "missing").length;
  const missingDays = buckets.reduce((sum, bucket) => sum + bucket.missingDays, 0);

  let tone: TrendTone = "stable";
  let statusLabel = "안정 흐름";
  let summaryText = "최근 흐름이 비교적 차분하게 유지되고 있습니다.";

  const hasHighMissingRisk =
    weeklyParticipation.triggered ||
    missingBuckets >= 1 ||
    missingDays >= Math.max(3, Math.ceil(bucketCount * 0.3));
  const hasDeclineRisk = declineBuckets >= Math.max(1, Math.ceil(bucketCount * 0.35));
  const hasChangeRisk = changeBuckets >= Math.max(1, Math.ceil(bucketCount * 0.35));

  if (hasHighMissingRisk) {
    tone = "down";
    statusLabel = "확인 필요";
    summaryText = "최근에는 대화 참여가 확인되지 않는 날이 보여 일상 리듬을 함께 살펴보는 것이 좋아요.";
  } else if (hasDeclineRisk) {
    tone = "alert";
    statusLabel = "변화 감지";
    summaryText = "최근 구간에서 이전보다 어려움이 늘어 보여 최근 일정을 함께 점검해보면 좋아요.";
  } else if (hasChangeRisk || missingDays >= 2) {
    tone = "alert";
    statusLabel = "변화 감지";
    summaryText = "예전과 다른 흐름이 관찰되어 최근 일정과 컨디션을 함께 확인해보면 좋아요.";
  }

  const signals: string[] = [];
  if (weeklyParticipation.triggered && weeklyParticipation.message) {
    signals.push(weeklyParticipation.message);
  }
  if (missingBuckets >= 1) {
    signals.push("일부 구간은 대화 참여 기록이 비어 있어 우선 확인이 필요합니다.");
  }
  if (declineBuckets >= 2) {
    signals.push("최근 구간에서 저하 흐름이 반복되어 생활 리듬 점검이 권장됩니다.");
  }
  if (missingDays >= 4) {
    signals.push("기록 공백이 있어 실제 상태보다 다르게 보일 수 있습니다.");
  }

  return {
    tone,
    statusLabel,
    summaryText,
    bucketCount,
    stableBuckets,
    changeBuckets,
    declineBuckets,
    missingBuckets,
    missingDays,
    signals,
  };
};

export const buildTrendBuckets = (points: TrendPoint[], rangeKey: TrendRangeKey): BucketedTrendResult => {
  const bucketSize = TREND_BUCKET_DAYS[rangeKey] ?? 1;
  const sorted = sortByDate(points);
  const bucketDrafts: Omit<TrendBucket, "state">[] = [];

  for (let index = 0; index < sorted.length; index += bucketSize) {
    const chunk = sorted.slice(index, index + bucketSize);
    if (!chunk.length) continue;

    const validValues = chunk
      .map((point) => point.value)
      .filter((value): value is number => value !== null && Number.isFinite(value));

    const startDate = chunk[0].date;
    const endDate = chunk[chunk.length - 1].date;

    bucketDrafts.push({
      index: bucketDrafts.length,
      startDate,
      endDate,
      label: formatMonthDay(endDate),
      value: averageOf(validValues),
      hasAnomaly: chunk.some((point) => point.flags.includes("ANOMALY")),
      missingDays: chunk.filter((point) => point.sampleCount <= 0).length,
      points: chunk,
    });
  }

  const validBucketValues = bucketDrafts
    .map((bucket) => bucket.value)
    .filter((value): value is number => value !== null && Number.isFinite(value));

  const mean =
    validBucketValues.length > 0
      ? validBucketValues.reduce((sum, value) => sum + value, 0) / validBucketValues.length
      : 0;
  const std = standardDeviation(validBucketValues);

  let previousValue: number | null = null;
  const buckets = bucketDrafts.map((bucket) => {
    const state = classifyBucketState(bucket, mean, std, previousValue);
    if (bucket.value !== null) {
      previousValue = bucket.value;
    }
    return { ...bucket, state };
  });

  const weeklyParticipation = buildWeeklyParticipationAlert(sorted);
  const metrics = buildMetrics(buckets, weeklyParticipation);

  return {
    buckets,
    values: buckets.map((bucket) =>
      bucket.state === "missing" ? null : STATE_LEVEL[bucket.state as Exclude<TrendState, "missing">]
    ),
    labels: buckets.map((bucket) => bucket.label),
    dates: buckets.map((bucket) => bucket.endDate),
    states: buckets.map((bucket) => bucket.state),
    highlights: buckets
      .filter((bucket) => bucket.state === "decline" || bucket.state === "change" || bucket.state === "missing")
      .map((bucket) => bucket.index),
    metrics,
    weeklyParticipation,
  };
};

export const findBucketIndexByDate = (buckets: TrendBucket[], isoDate: string) =>
  buckets.findIndex((bucket) => bucket.startDate <= isoDate && isoDate <= bucket.endDate);
