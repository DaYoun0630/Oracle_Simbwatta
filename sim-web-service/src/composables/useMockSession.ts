import { computed, ref } from "vue";

export type SessionSummary = {
  sessionId: string;
  startedAtISO: string;
  endedAtISO: string;
  userUtteranceCount: number;
  aiUtteranceCount: number;
  keywords: string[];
  riskLevel: "low" | "mid" | "high";
  riskScore: number;
  notes: string[];
};

export type HistoryItem = {
  sessionId: string;
  dateISO: string;
  title: string;
  riskLevel: "low" | "mid" | "high";
  riskScore: number;
};

const mockHistorySeed = (): HistoryItem[] => {
  const today = new Date();
  const items: HistoryItem[] = [];

  for (let i = 0; i < 10; i++) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);

    const dateISO = d.toISOString().slice(0, 10);
    const riskScore = 55 + ((Number(dateISO.replaceAll("-", "")) + i) % 35);

    const riskLevel =
      riskScore >= 80 ? "high" : riskScore >= 65 ? "mid" : "low";

    items.push({
      sessionId: `S-${dateISO.replaceAll("-", "")}-${i}`,
      dateISO,
      title: i % 2 === 0 ? "일상 대화" : "훈련 대화",
      riskLevel,
      riskScore,
    });
  }

  return items;
};

const historyStore = ref<HistoryItem[]>(mockHistorySeed());

export function useMockSession() {
  const history = computed(() => historyStore.value);

  const getSessionResult = (sessionId?: string): SessionSummary => {
    const now = new Date();
    const start = new Date(now);
    start.setMinutes(now.getMinutes() - 10);

    const safeSessionId = sessionId ?? `S-${now.toISOString().slice(0, 10)}`;

    const riskScore = 68;
    const riskLevel: SessionSummary["riskLevel"] =
      riskScore >= 80 ? "high" : riskScore >= 65 ? "mid" : "low";

    return {
      sessionId: safeSessionId,
      startedAtISO: start.toISOString(),
      endedAtISO: now.toISOString(),
      userUtteranceCount: 14,
      aiUtteranceCount: 12,
      keywords: ["피곤", "잠", "일정", "식사"],
      riskLevel,
      riskScore,
      notes: [
        "응답 속도가 평소보다 느렸던 구간이 있었어요.",
        "하루 컨디션(피곤/수면)에 대한 언급이 반복됐어요.",
      ],
    };
  };

  const getHistoryByDate = (dateISO: string) => {
    return historyStore.value.filter((x) => x.dateISO === dateISO);
  };

  return {
    history,
    getSessionResult,
    getHistoryByDate,
  };
}
