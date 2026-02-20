import type {
  TrendPoint,
  TrendQuery,
  TrendResponse,
  TrendSummary,
  WeeklyTrendViewModel,
} from "../contracts";
import type { TrendDataSource } from "../ports";

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));
const round1 = (value: number) => Math.round(value * 10) / 10;
const pad2 = (value: number) => String(value).padStart(2, "0");

const toDateOnly = (value: string) => {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    throw new Error(`Invalid date: ${value}`);
  }
  return date;
};

const toISODate = (date: Date) =>
  `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;

const buildDateRange = (startDate: string, endDate: string) => {
  const start = toDateOnly(startDate);
  const end = toDateOnly(endDate);
  if (start.getTime() > end.getTime()) {
    throw new Error("startDate must be earlier than endDate");
  }

  const days: string[] = [];
  const cursor = new Date(start);
  while (cursor.getTime() <= end.getTime()) {
    days.push(toISODate(cursor));
    cursor.setDate(cursor.getDate() + 1);
  }
  return days;
};

const dedupeFlags = (flags: string[]) => [...new Set(flags)];
const confidenceFromSample = (sampleCount: number) => clamp(0.25 + sampleCount * 0.12, 0, 1);

const normalizePoints = (response: TrendResponse, query: TrendQuery): TrendPoint[] => {
  const dateRange = buildDateRange(query.startDate, query.endDate);
  const pointMap = new Map(response.points.map((point) => [point.date, point]));

  return dateRange.map((date) => {
    const point = pointMap.get(date);
    if (!point) {
      return {
        date,
        value: null,
        sampleCount: 0,
        confidence: 0,
        flags: ["MISSING"],
      };
    }

    const sampleCount = Number.isFinite(point.sampleCount)
      ? Math.max(0, Math.floor(point.sampleCount))
      : 0;
    const value = sampleCount > 0 && Number.isFinite(point.value as number) ? round1(point.value as number) : null;
    const confidence = Number.isFinite(point.confidence)
      ? clamp(point.confidence, 0, 1)
      : confidenceFromSample(sampleCount);
    const flags = dedupeFlags([...(point.flags ?? [])]);

    if (sampleCount === 0) {
      flags.push("MISSING");
    } else if (sampleCount < 2) {
      flags.push("LOW_SAMPLE");
    }

    return {
      date,
      value,
      sampleCount,
      confidence,
      flags: dedupeFlags(flags),
    };
  });
};

const enrichAnomalyFlags = (points: TrendPoint[]) => {
  const validValues = points.map((point) => point.value).filter((value): value is number => value !== null);
  if (validValues.length < 3) return points;

  const mean = validValues.reduce((sum, value) => sum + value, 0) / validValues.length;
  const variance =
    validValues.reduce((sum, value) => sum + (value - mean) ** 2, 0) / Math.max(validValues.length - 1, 1);
  const std = Math.sqrt(variance);
  const threshold = Math.max(std * 1.4, 7);

  return points.map((point) => {
    if (point.value === null) return point;
    if (Math.abs(point.value - mean) < threshold) return point;
    return {
      ...point,
      flags: dedupeFlags([...point.flags, "ANOMALY"]),
    };
  });
};

const fallbackSummary = (points: TrendPoint[]): TrendSummary => {
  const validPoints = points.filter((point) => point.value !== null);
  if (validPoints.length < 3) {
    return {
      statusLabel: "유지 중",
      reason: "표본이 충분하지 않아 추세를 보수적으로 유지 중으로 표시합니다.",
      avg: null,
      deltaPercent: null,
    };
  }

  const first = validPoints[0].value as number;
  const last = validPoints[validPoints.length - 1].value as number;
  const avg = validPoints.reduce((sum, point) => sum + (point.value as number), 0) / validPoints.length;
  const deltaPercent = first === 0 ? 0 : ((last - first) / Math.abs(first)) * 100;
  const anomalyCount = validPoints.filter((point) => point.flags.includes("ANOMALY")).length;
  const lowSampleCount = validPoints.filter((point) => point.flags.includes("LOW_SAMPLE")).length;

  if (anomalyCount >= 2 || deltaPercent <= -8) {
    return {
      statusLabel: "관찰 필요",
      reason:
        anomalyCount >= 2
          ? "최근에는 변동이 큰 날이 반복되어 관찰이 필요합니다."
          : "최근 흐름이 전보다 내려가는 경향이 보여 관찰이 필요합니다.",
      avg: round1(avg),
      deltaPercent: round1(deltaPercent),
    };
  }

  if (deltaPercent >= 4 && anomalyCount === 0) {
    return {
      statusLabel: "안정 흐름",
      reason: "최근 반응 흐름이 비교적 부드럽게 유지되고 있습니다.",
      avg: round1(avg),
      deltaPercent: round1(deltaPercent),
    };
  }

  return {
    statusLabel: "유지 중",
    reason:
      lowSampleCount > 0
        ? "일부 날짜는 표본이 적어 보수적으로 유지 중 흐름으로 표시합니다."
        : "최근 흐름이 큰 변동 없이 유지되고 있습니다.",
    avg: round1(avg),
    deltaPercent: round1(deltaPercent),
  };
};

const toBadgeTone = (label: TrendSummary["statusLabel"]): WeeklyTrendViewModel["badgeTone"] => {
  if (label === "관찰 필요") return "down";
  if (label === "안정 흐름") return "up";
  return "stable";
};

const buildLabelFormatter = (pointCount: number, timezone?: string) => {
  const formatOptions: Intl.DateTimeFormatOptions =
    pointCount > 14
      ? { month: "numeric", day: "numeric", timeZone: timezone || "Asia/Seoul" }
      : { weekday: "short", timeZone: timezone || "Asia/Seoul" };

  try {
    return new Intl.DateTimeFormat("ko-KR", formatOptions);
  } catch {
    return pointCount > 14
      ? new Intl.DateTimeFormat("ko-KR", { month: "numeric", day: "numeric" })
      : new Intl.DateTimeFormat("ko-KR", { weekday: "short" });
  }
};

export const createWeeklyTrendUseCase = (dataSource: TrendDataSource) => {
  const getWeeklyTrend = async (query: TrendQuery): Promise<WeeklyTrendViewModel> => {
    const response = await dataSource.fetchWeeklyTrend(query);
    const normalizedPoints = normalizePoints(response, query);
    const analyzedPoints = enrichAnomalyFlags(normalizedPoints);
    const computedSummary = fallbackSummary(analyzedPoints);

    const summary: TrendSummary = {
      ...computedSummary,
      statusLabel: response.summary?.statusLabel ?? computedSummary.statusLabel,
      reason: response.summary?.reason || computedSummary.reason,
    };

    const formatter = buildLabelFormatter(analyzedPoints.length, query.timezone);
    const labels = analyzedPoints.map((point) => formatter.format(toDateOnly(point.date)));
    const values = analyzedPoints.map((point) => point.value);
    const highlights = analyzedPoints
      .map((point, index) => (point.flags.includes("ANOMALY") ? index : -1))
      .filter((index) => index >= 0);

    return {
      points: analyzedPoints,
      labels,
      values,
      highlights,
      badgeTone: toBadgeTone(summary.statusLabel),
      badgeText: summary.statusLabel,
      summaryText: summary.reason,
      hintText: "표식은 평소 흐름과 다른 변화를 요약해 보여줍니다.",
      meta: response.meta,
    };
  };

  return { getWeeklyTrend };
};
