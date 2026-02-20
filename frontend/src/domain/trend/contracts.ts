export type TrendFlag = "ANOMALY" | "LOW_SAMPLE" | "MISSING";

export interface TrendQuery {
  subjectId: string;
  startDate: string; // YYYY-MM-DD
  endDate: string; // YYYY-MM-DD
  timezone?: string;
}

export interface TrendPoint {
  date: string; // YYYY-MM-DD
  value: number | null;
  sampleCount: number;
  confidence: number; // 0..1
  flags: TrendFlag[];
}

export interface TrendSummary {
  statusLabel: "안정 흐름" | "관찰 필요" | "유지 중";
  reason: string;
  avg: number | null;
  deltaPercent: number | null;
}

export interface TrendResponse {
  startDate: string;
  endDate: string;
  points: TrendPoint[];
  summary: TrendSummary;
  meta: {
    source: string;
    generatedAt: string;
  };
}

export interface WeeklyTrendViewModel {
  points: TrendPoint[];
  labels: string[];
  values: Array<number | null>;
  highlights: number[];
  badgeTone: "up" | "down" | "stable";
  badgeText: TrendSummary["statusLabel"];
  summaryText: string;
  hintText: string;
  meta: TrendResponse["meta"];
}
