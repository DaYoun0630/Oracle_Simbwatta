import type { TrendQuery } from "@/domain/trend/contracts";

export type TrendRangeKey = "7d" | "1m" | "3m" | "6m";

export interface TrendRangeOption {
  key: TrendRangeKey;
  label: string;
  heading: string;
  days: number;
}

export const TREND_RANGE_OPTIONS: TrendRangeOption[] = [
  { key: "7d", label: "\uC77C\uC8FC\uC77C", heading: "\uCD5C\uADFC 7\uC77C", days: 7 },
  { key: "1m", label: "1\uAC1C\uC6D4", heading: "\uCD5C\uADFC 1\uAC1C\uC6D4", days: 30 },
  { key: "3m", label: "3\uAC1C\uC6D4", heading: "\uCD5C\uADFC 3\uAC1C\uC6D4", days: 90 },
  { key: "6m", label: "6\uAC1C\uC6D4", heading: "\uCD5C\uADFC 6\uAC1C\uC6D4", days: 180 },
];

export const TREND_BUCKET_DAYS: Record<TrendRangeKey, number> = {
  "7d": 1,
  "1m": 7,
  "3m": 14,
  "6m": 28,
};

const DEFAULT_SUBJECT_ID = "subject-001";
const DEFAULT_TIMEZONE = "Asia/Seoul";

const pad2 = (value: number) => String(value).padStart(2, "0");

export const toLocalISODate = (date: Date) =>
  `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;

const getRangeOption = (key: TrendRangeKey) =>
  TREND_RANGE_OPTIONS.find((option) => option.key === key) ?? TREND_RANGE_OPTIONS[0];

export const getTrendRangeLabel = (key: TrendRangeKey) => getRangeOption(key).label;
export const getTrendRangeHeading = (key: TrendRangeKey) => getRangeOption(key).heading;

export const getTrendDateRange = (key: TrendRangeKey, baseDate: Date = new Date()) => {
  const option = getRangeOption(key);
  const endDate = new Date(baseDate);
  endDate.setDate(endDate.getDate() - 1);
  const startDate = new Date(endDate);
  startDate.setDate(endDate.getDate() - (option.days - 1));

  return {
    startDate: toLocalISODate(startDate),
    endDate: toLocalISODate(endDate),
  };
};

export const buildTrendQueryForRange = (
  key: TrendRangeKey,
  overrides: Partial<TrendQuery> = {}
): TrendQuery => {
  const range = getTrendDateRange(key);
  return {
    subjectId: overrides.subjectId ?? DEFAULT_SUBJECT_ID,
    startDate: overrides.startDate ?? range.startDate,
    endDate: overrides.endDate ?? range.endDate,
    timezone: overrides.timezone ?? DEFAULT_TIMEZONE,
  };
};
