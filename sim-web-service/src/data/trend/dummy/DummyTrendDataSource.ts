import type { TrendDataSource } from "@/domain/trend/ports";
import type { TrendFlag, TrendPoint, TrendQuery, TrendResponse } from "@/domain/trend/contracts";

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));
const round1 = (value: number) => Math.round(value * 10) / 10;
const pad2 = (value: number) => String(value).padStart(2, "0");
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

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

  const dates: string[] = [];
  const cursor = new Date(start);
  while (cursor.getTime() <= end.getTime()) {
    dates.push(toISODate(cursor));
    cursor.setDate(cursor.getDate() + 1);
  }
  return dates;
};

const hashString = (value: string) => {
  let hash = 2166136261;
  for (let i = 0; i < value.length; i += 1) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
};

const mulberry32 = (seed: number) => {
  let state = seed >>> 0;
  return () => {
    state += 0x6d2b79f5;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
};

const appendAnomalyFlags = (points: TrendPoint[]) => {
  const valid = points.filter((point) => point.value !== null);
  if (valid.length < 3) return points;

  const mean = valid.reduce((sum, point) => sum + (point.value as number), 0) / valid.length;
  const variance =
    valid.reduce((sum, point) => sum + ((point.value as number) - mean) ** 2, 0) / Math.max(valid.length - 1, 1);
  const std = Math.sqrt(variance);
  const threshold = Math.max(std * 1.4, 7);

  return points.map((point) => {
    if (point.value === null) return point;
    if (Math.abs(point.value - mean) < threshold) return point;
    return {
      ...point,
      flags: [...new Set([...point.flags, "ANOMALY"])],
    };
  });
};

const summarize = (points: TrendPoint[]) => {
  const valid = points.filter((point) => point.value !== null);
  if (valid.length < 3) {
    return {
      statusLabel: "유지 중" as const,
      reason: "표본이 충분하지 않아 추세를 보수적으로 유지 중으로 표시합니다.",
      avg: null,
      deltaPercent: null,
    };
  }

  const first = valid[0].value as number;
  const last = valid[valid.length - 1].value as number;
  const avg = valid.reduce((sum, point) => sum + (point.value as number), 0) / valid.length;
  const deltaPercent = first === 0 ? 0 : ((last - first) / Math.abs(first)) * 100;
  const anomalyCount = valid.filter((point) => point.flags.includes("ANOMALY")).length;

  if (anomalyCount >= 2 || deltaPercent <= -8) {
    return {
      statusLabel: "관찰 필요" as const,
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
      statusLabel: "안정 흐름" as const,
      reason: "최근 반응 흐름이 비교적 부드럽게 유지되고 있습니다.",
      avg: round1(avg),
      deltaPercent: round1(deltaPercent),
    };
  }

  return {
    statusLabel: "유지 중" as const,
    reason: "최근 흐름이 큰 변동 없이 유지되고 있습니다.",
    avg: round1(avg),
    deltaPercent: round1(deltaPercent),
  };
};

const buildInitialFlags = (sampleCount: number): TrendFlag[] => {
  if (sampleCount <= 0) return ["MISSING"];
  if (sampleCount < 2) return ["LOW_SAMPLE"];
  return [];
};

const SERIES_DAYS = 180;
const STABLE_PHASE_DAYS = 120;
const seriesCache = new Map<string, TrendPoint[]>();

const RECENT_WEEK_TEMPLATE: ReadonlyArray<{ value: number | null; sampleCount: number }> = [
  { value: 66, sampleCount: 3 },
  { value: 74, sampleCount: 4 },
  { value: null, sampleCount: 0 },
  { value: 70, sampleCount: 2 },
  { value: 66, sampleCount: 2 },
  { value: 62, sampleCount: 1 },
  { value: 62, sampleCount: 1 },
];

const applyRecentWeekScenario = (series: TrendPoint[]) => {
  if (series.length < RECENT_WEEK_TEMPLATE.length) return series;

  const startIndex = series.length - RECENT_WEEK_TEMPLATE.length;
  const recentValidValues = series
    .slice(startIndex)
    .map((point) => point.value)
    .filter((value): value is number => value !== null && Number.isFinite(value));
  const anchor = recentValidValues.length
    ? round1(recentValidValues.reduce((sum, value) => sum + value, 0) / recentValidValues.length)
    : 67;
  const shift = anchor - 67;

  return series.map((point, index) => {
    if (index < startIndex) return point;

    const template = RECENT_WEEK_TEMPLATE[index - startIndex];
    const sampleCount = template.sampleCount;
    const value = template.value === null ? null : clamp(round1(template.value + shift), 40, 96);
    const confidence = sampleCount > 0 ? clamp(0.34 + sampleCount * 0.09, 0, 1) : 0;

    return {
      ...point,
      value,
      sampleCount,
      confidence: round1(confidence * 100) / 100,
      flags: buildInitialFlags(sampleCount),
    };
  });
};

const buildSixMonthSeries = (subjectId: string, endDateText: string) => {
  const cacheKey = `${subjectId}:${endDateText}`;
  const cached = seriesCache.get(cacheKey);
  if (cached) return cached;

  const endDate = toDateOnly(endDateText);
  const startDate = new Date(endDate);
  startDate.setDate(endDate.getDate() - (SERIES_DAYS - 1));
  const seriesDates = buildDateRange(toISODate(startDate), endDateText);
  const seedRandom = mulberry32(hashString(`${subjectId}:six-month-seed`));
  const baselineHigh = 83 + seedRandom() * 2.5;
  const declineRange = 12 + seedRandom() * 3;

  const rawSeries = seriesDates.map((date, index) => {
    const dayRandom = mulberry32(hashString(`${subjectId}:${date}`));
    const earlyProgress = Math.min(index / Math.max(STABLE_PHASE_DAYS - 1, 1), 1);
    const declineProgress =
      index < STABLE_PHASE_DAYS
        ? 0
        : (index - STABLE_PHASE_DAYS) / Math.max(SERIES_DAYS - STABLE_PHASE_DAYS - 1, 1);
    const decline = declineRange * Math.pow(declineProgress, 1.35);

    const seasonalAmp =
      declineProgress === 0
        ? lerp(0.5, 0.9, earlyProgress)
        : lerp(1.2, 2.3, Math.min(declineProgress, 1));
    const noiseAmp =
      declineProgress === 0
        ? lerp(0.5, 1.0, earlyProgress)
        : lerp(1.1, 2.4, Math.min(declineProgress, 1));
    const seasonal = Math.sin(index * 0.21) * seasonalAmp + Math.cos(index * 0.08) * (seasonalAmp * 0.68);
    const noise = (dayRandom() - 0.5) * noiseAmp;
    const baseValue = baselineHigh - decline + seasonal + noise;

    let sampleCount = Math.max(0, Math.floor(dayRandom() * 8));
    if (index < STABLE_PHASE_DAYS) {
      sampleCount = Math.max(sampleCount, 2);
    }

    const hasSample = sampleCount > 0;
    const anomalyDip = index % 57 === 32 ? -4.5 : 0;
    const value = hasSample ? clamp(round1(baseValue + anomalyDip), 40, 96) : null;
    const confidence = hasSample ? clamp(0.32 + sampleCount * 0.09 + dayRandom() * 0.08, 0, 1) : 0;

    return {
      date,
      value,
      sampleCount,
      confidence: round1(confidence * 100) / 100,
      flags: buildInitialFlags(sampleCount),
    } as TrendPoint;
  });

  const scenarioSeries = applyRecentWeekScenario(rawSeries);
  const recentScenarioStart = Math.max(0, scenarioSeries.length - RECENT_WEEK_TEMPLATE.length);
  const flaggedSeries = appendAnomalyFlags(scenarioSeries).map((point, index) => {
    if (index < recentScenarioStart) return point;
    return {
      ...point,
      flags: point.flags.filter((flag) => flag !== "ANOMALY"),
    };
  });

  seriesCache.set(cacheKey, flaggedSeries);
  return flaggedSeries;
};

export class DummyTrendDataSource implements TrendDataSource {
  async fetchWeeklyTrend(query: TrendQuery): Promise<TrendResponse> {
    const dates = buildDateRange(query.startDate, query.endDate);
    const sixMonthSeries = buildSixMonthSeries(query.subjectId, query.endDate);
    const pointMap = new Map(sixMonthSeries.map((point) => [point.date, point]));
    const pointsWithFlags = dates.map((date) => {
      const point = pointMap.get(date);
      if (point) return point;
      return {
        date,
        value: null,
        sampleCount: 0,
        confidence: 0,
        flags: ["MISSING"] as TrendFlag[],
      };
    });

    return {
      startDate: query.startDate,
      endDate: query.endDate,
      points: pointsWithFlags,
      summary: summarize(pointsWithFlags),
      meta: {
        source: "dummy-six-month",
        generatedAt: new Date().toISOString(),
      },
    };
  }
}
