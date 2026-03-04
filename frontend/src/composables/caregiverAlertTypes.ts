export type AlertAxis = "participation" | "training" | "speech";
export type AlertTone = "info" | "suggest" | "caution" | "consult";
export type AlertKind = "trigger" | "summary";

export interface CaregiverAlert {
  id: string;
  axis: AlertAxis;
  tone: AlertTone;
  kind: AlertKind;
  titleLine: string;
  actionLine: string;
  tagLabel: "참여" | "훈련" | "발화";
  startDate: string;
  endDate: string;
}

export const ALERT_AXIS_PRIORITY: AlertAxis[] = ["speech", "participation", "training"];

export const ALERT_TAG_LABEL: Record<AlertAxis, CaregiverAlert["tagLabel"]> = {
  participation: "참여",
  training: "훈련",
  speech: "발화",
};

export const ALERT_TONE_RANK: Record<AlertTone, number> = {
  info: 1,
  suggest: 2,
  caution: 3,
  consult: 4,
};

export const ALERT_KIND_LABEL: Record<AlertKind, string> = {
  trigger: "모니터링 알림",
  summary: "기간 요약",
};

export const ALERT_TONE_LABEL: Record<AlertTone, string> = {
  info: "정보",
  suggest: "권장",
  caution: "주의",
  consult: "상담 제안",
};

const DIGIT_PATTERN = /[0-9]/;
const FORBIDDEN_WORDS = ["점수", "평가"];

export const ensureSafeAlertLine = (value: string, fallback: string) => {
  if (!value) return fallback;
  if (DIGIT_PATTERN.test(value)) return fallback;
  if (FORBIDDEN_WORDS.some((word) => value.includes(word))) return fallback;
  return value;
};

export const sortAlertsByPriority = (alerts: CaregiverAlert[]) => {
  const axisRank = new Map(ALERT_AXIS_PRIORITY.map((axis, index) => [axis, index]));
  return [...alerts].sort((a, b) => {
    const toneGap = ALERT_TONE_RANK[b.tone] - ALERT_TONE_RANK[a.tone];
    if (toneGap !== 0) return toneGap;
    const kindGap = Number(b.kind === "trigger") - Number(a.kind === "trigger");
    if (kindGap !== 0) return kindGap;
    return (axisRank.get(a.axis) ?? 99) - (axisRank.get(b.axis) ?? 99);
  });
};
