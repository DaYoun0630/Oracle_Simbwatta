import type { TrendRangeKey } from "@/composables/useTrendRange";

export type ObservationDomain = "training" | "speech" | "participation";
export type ObservationSeverity = "가벼움" | "주의" | "뚜렷함";
export type DailyTrendLevel = "stable" | "change" | "decline" | "missing";

export interface EvidenceLog {
  date: string;
  detail: string;
}

export interface DailyTrendPoint {
  date: string;
  level: DailyTrendLevel;
  flags: string[];
  metrics: {
    interruptions: number;
    responseDelayPercent: number;
    participationGap: boolean;
  };
}

export interface ComparisonRow {
  label: string;
  current: string;
  previous: string;
}

export interface PeriodSummary {
  status: "안정" | "변화" | "저하" | "미참여";
  evidenceMetrics: string;
  recommendedAction: string;
  dateRangeLabel: string;
  quickStats: string[];
  comparisonRows: ComparisonRow[];
}

export interface ObservationItem {
  domain: ObservationDomain;
  severity: ObservationSeverity;
  title: string;
  deltaMetrics: string;
  evidenceLogs: EvidenceLog[];
  actions: string[];
}

export interface NotableChange {
  domain: ObservationDomain;
  whenLabel: string;
  title: string;
  actionTip: string;
}

export interface CaregiverRecordPageModel {
  range: TrendRangeKey;
  periodSummary: PeriodSummary;
  dailyTrendPoints: DailyTrendPoint[];
  observationItems: ObservationItem[];
  notableChanges: NotableChange[];
  rawLogs: EvidenceLog[];
}

export interface CaregiverRecordProvider {
  getRecord(range: TrendRangeKey): Promise<CaregiverRecordPageModel>;
}
