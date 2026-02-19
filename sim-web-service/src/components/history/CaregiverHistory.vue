<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import WeeklyChart from "../WeeklyChart.vue";
import { useWeeklyTrend } from "@/composables/useWeeklyTrend";
import { buildTrendBuckets } from "@/composables/useTrendBuckets";
import {
  TREND_RANGE_OPTIONS,
  buildTrendQueryForRange,
  type TrendRangeKey,
} from "@/composables/useTrendRange";
import { buildCaregiverAlertBundle } from "@/composables/useCaregiverAlerts";
import type { AlertAxis, AlertTone, CaregiverAlert } from "@/composables/caregiverAlertTypes";

const AXIS_VALUES: AlertAxis[] = ["participation", "training", "speech"];

const isTrendRangeKey = (value: unknown): value is TrendRangeKey =>
  typeof value === "string" && TREND_RANGE_OPTIONS.some((option) => option.key === value);
const isAlertAxis = (value: unknown): value is AlertAxis =>
  typeof value === "string" && AXIS_VALUES.includes(value as AlertAxis);

const route = useRoute();
const router = useRouter();
const { trend, loading: trendLoading, error: trendError, fetchWeeklyTrend } = useWeeklyTrend();

const selectedRange = ref<TrendRangeKey>("7d");
const focusedAxis = ref<AlertAxis | null>(null);
const chartHelpOpen = ref(false);

const fetchTrendByRange = async (rangeKey: TrendRangeKey = selectedRange.value) =>
  fetchWeeklyTrend(buildTrendQueryForRange(rangeKey));

const syncStateFromRoute = (fetchOnRangeChange: boolean) => {
  const periodQuery = route.query.period;
  const axisQuery = route.query.axis;

  const nextRange = isTrendRangeKey(periodQuery) ? periodQuery : "7d";
  const nextAxis = isAlertAxis(axisQuery) ? axisQuery : null;

  const rangeChanged = selectedRange.value !== nextRange;
  selectedRange.value = nextRange;
  focusedAxis.value = nextAxis;

  if (fetchOnRangeChange && rangeChanged) {
    void fetchTrendByRange(nextRange);
  }
};

const syncRouteFromState = () => {
  const nextQuery = {
    ...route.query,
    period: selectedRange.value,
  } as Record<string, string>;

  delete nextQuery.tab;

  if (focusedAxis.value) {
    nextQuery.axis = focusedAxis.value;
  } else {
    delete nextQuery.axis;
  }

  const currentPeriod = typeof route.query.period === "string" ? route.query.period : "";
  const currentAxis = typeof route.query.axis === "string" ? route.query.axis : "";
  const nextAxis = nextQuery.axis ?? "";

  if (currentPeriod === nextQuery.period && currentAxis === nextAxis) return;
  router.replace({ query: nextQuery });
};

onMounted(() => {
  syncStateFromRoute(false);
  void fetchTrendByRange(selectedRange.value);
});

watch(
  () => route.query,
  () => {
    syncStateFromRoute(true);
  }
);

watch([selectedRange, focusedAxis], () => {
  syncRouteFromState();
});

const handleRangeSelect = (rangeKey: TrendRangeKey) => {
  if (selectedRange.value === rangeKey && trend.value) return;
  selectedRange.value = rangeKey;
  void fetchTrendByRange(rangeKey);
};

const handleAxisFocus = (axis: AlertAxis) => {
  focusedAxis.value = focusedAxis.value === axis ? null : axis;
};

const bucketedTrend = computed(() => buildTrendBuckets(trend.value?.points ?? [], selectedRange.value));
const alertBundle = computed(() => buildCaregiverAlertBundle(selectedRange.value, bucketedTrend.value));

const trendValues = computed<Array<number | null>>(() => bucketedTrend.value.values);
const trendLabels = computed(() => bucketedTrend.value.labels);
const trendDates = computed(() => bucketedTrend.value.dates);
const trendStates = computed(() => bucketedTrend.value.states);
const highlightIndices = computed(() => bucketedTrend.value.highlights);

const toneRank: Record<AlertTone, number> = {
  info: 1,
  suggest: 2,
  caution: 3,
  consult: 4,
};

const toneToStrength = (tone: AlertTone) => {
  if (tone === "consult" || tone === "caution") return "뚜렷함";
  if (tone === "suggest") return "보통";
  return "가벼움";
};

const buildCompareText = (axis: AlertAxis, tone: AlertTone) => {
  const level =
    tone === "consult" || tone === "caution"
      ? "늘어난 편"
      : tone === "suggest"
      ? "조금 늘어난 편"
      : "비슷해요";

  if (axis === "participation") return `지난 기간보다 참여 공백이 ${level}.`;
  if (axis === "training") return `지난 기간보다 수행 어려움이 ${level}.`;
  return `지난 기간보다 대화 끊김이 ${level}.`;
};

const sortByTone = (alerts: CaregiverAlert[]) =>
  [...alerts].sort((a, b) => toneRank[b.tone] - toneRank[a.tone]);

const summaryPrimary = computed(() => sortByTone(alertBundle.value.summaryAlerts)[0] ?? null);

const summaryHeadline = computed(() => {
  const tone = summaryPrimary.value?.tone;
  if (tone === "consult" || tone === "caution") return "이번 기간은 저하 흐름이 나타났어요.";
  if (tone === "suggest") return "이번 기간은 이전과 다른 흐름이 보여요.";
  return "이번 기간은 대체로 안정적이에요.";
});

const summaryStrength = computed(() => toneToStrength(summaryPrimary.value?.tone ?? "info"));

const observationCards = computed(() => {
  const sorted = sortByTone(alertBundle.value.summaryAlerts);
  return sorted.slice(0, 3).map((alert) => ({
    id: alert.id,
    axis: alert.axis,
    axisLabel: alert.tagLabel,
    strength: toneToStrength(alert.tone),
    title: alert.titleLine,
    compareText: buildCompareText(alert.axis, alert.tone),
  }));
});

const toRelativeDay = (isoDate: string) => {
  const target = new Date(`${isoDate}T00:00:00`);
  if (Number.isNaN(target.getTime())) return isoDate;

  const today = new Date();
  const base = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const date = new Date(target.getFullYear(), target.getMonth(), target.getDate());
  const diff = Math.round((base.getTime() - date.getTime()) / (24 * 60 * 60 * 1000));

  if (diff <= 0) return "오늘";
  if (diff === 1) return "어제";
  if (diff <= 6) return `${diff}일 전`;
  return `${target.getMonth() + 1}.${target.getDate()}`;
};

const compactLine = (value: string, maxLength = 28) => {
  const text = value.replace(/\s+/g, " ").trim();
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength)}...`;
};

const compactReason = (value: string) => {
  const text = value.replace(/\s+/g, " ").trim();
  if (!text) return "평소와 다른 흐름이 보였어요";
  return text.split(/[.?!]/)[0].trim();
};

const eventItems = computed(() => {
  const base =
    focusedAxis.value === null
      ? alertBundle.value.monitoringAlerts
      : alertBundle.value.monitoringAlerts.filter((alert) => alert.axis === focusedAxis.value);

  return base.map((alert) => ({
    id: alert.id,
    axis: alert.axis,
    axisLabel: alert.tagLabel,
    when: toRelativeDay(alert.endDate),
    title: compactLine(alert.titleLine, 44),
    reason: compactReason(alert.actionLine),
  }));
});

const rangePanelNoteMap: Record<TrendRangeKey, string> = {
  "7d": "일주일 흐름은 하루 단위 변화를 기준으로 정리했어요.",
  "1m": "1개월 흐름은 주간 평균 변화를 중심으로 정리했어요.",
  "3m": "3개월 흐름은 격주 단위 추세를 한눈에 볼 수 있게 정리했어요.",
  "6m": "6개월 흐름은 장기 변화의 방향을 확인하기 쉽게 정리했어요.",
};

const rangePanelNote = computed(() => rangePanelNoteMap[selectedRange.value]);
</script>

<template>
  <div class="history-container">
    <div v-if="trendLoading && !trend" class="loading">
      <div class="spinner"></div>
    </div>

    <template v-else>
      <section class="range-bar">
        <div class="range-controls" role="group" aria-label="관찰 기간 선택">
          <button
            v-for="option in TREND_RANGE_OPTIONS"
            :key="option.key"
            type="button"
            class="range-button"
            :class="{ active: selectedRange === option.key }"
            :aria-pressed="selectedRange === option.key"
            @click="handleRangeSelect(option.key)"
          >
            {{ option.label }}
          </button>
        </div>
      </section>

      <section class="panel-card">
        <div class="summary-head">
          <h3>기간 추세</h3>
          <span class="strength-chip">{{ summaryStrength }}</span>
        </div>
        <p class="summary-headline">{{ summaryHeadline }}</p>

        <WeeklyChart
          :data="trendValues"
          :labels="trendLabels"
          :dates="trendDates"
          :states="trendStates"
          :highlights="highlightIndices"
          :y-state-labels="['안정', '변화', '저하', '미참여']"
        />

        <button type="button" class="help-toggle" @click="chartHelpOpen = !chartHelpOpen">
          {{ chartHelpOpen ? "차트 해석 닫기" : "ℹ️ 차트 해석 보기" }}
        </button>
        <p v-if="chartHelpOpen" class="help-text">
          점과 선은 상태 추세를, 하단 미참여 표시는 기록 공백을 뜻합니다.
        </p>

        <p class="panel-note">{{ rangePanelNote }}</p>
        <p v-if="trendError" class="panel-note error">{{ trendError }}</p>
      </section>

      <section class="panel-card">
        <h3>관찰 포인트</h3>
        <div class="observation-grid">
          <article
            v-for="card in observationCards"
            :key="card.id"
            class="observation-card"
            :class="{ focused: focusedAxis === card.axis }"
            @click="handleAxisFocus(card.axis)"
          >
            <div class="observation-head">
              <span class="axis-tag">{{ card.axisLabel }}</span>
              <span class="strength-tag">{{ card.strength }}</span>
            </div>
            <p class="observation-title">{{ card.title }}</p>
            <p class="observation-compare">{{ card.compareText }}</p>
          </article>
        </div>
      </section>

      <section v-if="eventItems.length" class="panel-card">
        <h3>눈여겨볼 변화</h3>
        <div class="event-list">
          <article v-for="item in eventItems" :key="item.id" class="event-item">
            <div class="event-head">
              <span class="event-axis">{{ item.axisLabel }}</span>
              <span class="event-when">{{ item.when }}</span>
            </div>
            <p class="event-title">{{ item.title }}</p>
            <p class="event-reason">{{ item.reason }}</p>
          </article>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.history-container {
  --card-surface: #f7f9fa;
  --card-elevation-main:
    0 10px 22px rgba(126, 140, 154, 0.18),
    0 3px 8px rgba(126, 140, 154, 0.11),
    0 1px 3px rgba(126, 140, 154, 0.06);
  --card-elevation-sub:
    0 8px 16px rgba(126, 140, 154, 0.14),
    0 2px 6px rgba(126, 140, 154, 0.1);
  --card-elevation-hover:
    0 11px 20px rgba(126, 140, 154, 0.16),
    0 4px 10px rgba(126, 140, 154, 0.12);
  display: grid;
  gap: 14px;
  width: 100%;
  min-height: 100%;
}

.loading {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 220px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #d9e0e3;
  border-top-color: #4cb7b7;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.range-bar {
  position: sticky;
  top: 0;
  z-index: 5;
  background: rgba(244, 247, 248, 0.92);
  padding-top: 2px;
  backdrop-filter: blur(2px);
}

.range-controls {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.range-button {
  border: none;
  border-radius: 999px;
  padding: 8px 10px;
  font-size: 13px;
  font-weight: 800;
  color: #5f6b73;
  background: #eef3f5;
  box-shadow: inset 2px 2px 4px rgba(129, 142, 153, 0.2), inset -2px -2px 4px rgba(255, 255, 255, 0.95);
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, background-color 0.18s ease, color 0.18s ease;
}

.range-button:hover {
  transform: translateY(-1px);
}

.range-button.active {
  color: #ffffff;
  background: #4cb7b7;
  box-shadow: 0 6px 12px rgba(76, 183, 183, 0.28);
}

.panel-card {
  background: var(--card-surface);
  border-radius: 22px;
  box-shadow: var(--card-elevation-main);
  padding: 16px 14px;
  display: grid;
  gap: 10px;
}

.summary-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.summary-head h3,
.panel-card h3 {
  margin: 0;
  font-size: 21px;
  font-weight: 900;
  color: #2e2e2e;
}

.strength-chip {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 800;
  color: #51616b;
  background: #eaf1f4;
}

.summary-headline {
  margin: 0;
  font-size: 18px;
  font-weight: 900;
  line-height: 1.45;
  color: #30363a;
}

.help-toggle {
  border: none;
  justify-self: start;
  border-radius: 999px;
  background: #eaf1f4;
  color: #51616b;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.help-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.45;
  color: #67727b;
}

.panel-note {
  margin: 0;
  font-size: 14px;
  line-height: 1.45;
  color: #66737c;
  background: #eef3f5;
  border-radius: 12px;
  padding: 10px 12px;
}

.panel-note.error {
  color: #d87a71;
}

.observation-grid {
  display: grid;
  gap: 10px;
}

.observation-card {
  border-radius: 16px;
  background: #f8fbfb;
  box-shadow: var(--card-elevation-sub);
  padding: 12px 13px;
  display: grid;
  gap: 8px;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.observation-card:hover {
  transform: translateY(-1px);
  box-shadow: var(--card-elevation-hover);
}

.observation-card.focused {
  box-shadow:
    0 0 0 2px rgba(76, 183, 183, 0.2),
    var(--card-elevation-sub);
}

.observation-head {
  display: flex;
  align-items: center;
  gap: 7px;
}

.axis-tag,
.strength-tag {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 4px 9px;
  font-size: 12px;
  font-weight: 800;
}

.axis-tag {
  background: #eaf1f4;
  color: #55626b;
}

.strength-tag {
  background: rgba(255, 183, 77, 0.2);
  color: #b57d2d;
}

.observation-title {
  margin: 0;
  font-size: 16px;
  font-weight: 900;
  line-height: 1.45;
  color: #30363a;
}

.observation-compare {
  margin: 0;
  font-size: 14px;
  line-height: 1.45;
  color: #4f5d66;
}

.event-list {
  display: grid;
  gap: 8px;
}

.event-item {
  border-radius: 14px;
  background: #ffffff;
  box-shadow: var(--card-elevation-sub);
  padding: 12px 13px;
  display: grid;
  gap: 7px;
}

.event-head {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.event-axis,
.event-when {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 4px 9px;
  font-size: 12px;
  font-weight: 800;
}

.event-axis {
  background: #eaf1f4;
  color: #55626b;
}

.event-when {
  background: rgba(255, 183, 77, 0.2);
  color: #9f6f28;
}

.event-title {
  margin: 0;
  font-size: 16px;
  font-weight: 900;
  line-height: 1.45;
  color: #28363f;
}

.event-reason {
  margin: 0;
  font-size: 14px;
  line-height: 1.55;
  color: #4f5d66;
}

@media (max-width: 560px) {
  .summary-head h3,
  .panel-card h3 {
    font-size: 19px;
  }

  .summary-headline {
    font-size: 17px;
  }
}
</style>
