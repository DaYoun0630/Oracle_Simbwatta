<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import WeeklyChart from "../WeeklyChart.vue";
import { TREND_RANGE_OPTIONS, type TrendRangeKey } from "@/composables/useTrendRange";
import { createCaregiverRecordProvider } from "./caregiverRecord/createCaregiverRecordProvider";
import type {
  CaregiverRecordPageModel,
  DailyTrendPoint,
  ObservationDomain,
  ObservationItem,
  ObservationSeverity,
} from "./caregiverRecord/types";

const DOMAIN_ORDER: ObservationDomain[] = ["training", "speech", "participation"];
const DOMAIN_LABEL: Record<ObservationDomain, string> = {
  training: "훈련",
  speech: "발화",
  participation: "참여",
};
const LEVEL_TEXT: Record<DailyTrendPoint["level"], string> = {
  stable: "안정",
  change: "변화",
  decline: "저하",
  missing: "미측정",
};
const VALUE_BY_LEVEL: Record<Exclude<DailyTrendPoint["level"], "missing">, number> = {
  stable: 2,
  change: 1,
  decline: 0,
};
const TREND_RANGE_POLICY: Record<TrendRangeKey, { rangeDays: number; bucketSize: number; pointCount: number }> = {
  "7d": { rangeDays: 7, bucketSize: 1, pointCount: 7 },
  "1m": { rangeDays: 30, bucketSize: 5, pointCount: 6 },
  "3m": { rangeDays: 90, bucketSize: 15, pointCount: 6 },
  "6m": { rangeDays: 182, bucketSize: 7, pointCount: 6 },
};

const route = useRoute();
const router = useRouter();
const recordProvider = createCaregiverRecordProvider();

const selectedRange = ref<TrendRangeKey>("7d");
const loading = ref(false);
const error = ref<string | null>(null);
const record = ref<CaregiverRecordPageModel | null>(null);
const selectedPointIndex = ref<number | null>(null);
const interpretationSheetOpen = ref(false);
const compareSectionOpen = ref(false);
const rawLogSectionOpen = ref(false);

const isTrendRangeKey = (value: unknown): value is TrendRangeKey =>
  typeof value === "string" && TREND_RANGE_OPTIONS.some((option) => option.key === value);

const syncRangeFromRoute = () => {
  const periodQuery = route.query.period;
  selectedRange.value = isTrendRangeKey(periodQuery) ? periodQuery : "7d";
};

const syncRouteFromRange = () => {
  const nextQuery = { ...route.query, period: selectedRange.value } as Record<string, string>;
  delete nextQuery.tab;
  delete nextQuery.axis;

  const currentPeriod = typeof route.query.period === "string" ? route.query.period : "";
  if (currentPeriod === nextQuery.period) return;
  router.replace({ query: nextQuery });
};

const fetchRecord = async (range: TrendRangeKey) => {
  loading.value = true;
  error.value = null;
  try {
    record.value = await recordProvider.getRecord(range);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "기록 데이터를 불러오지 못했습니다.";
    record.value = null;
  } finally {
    loading.value = false;
  }
};

onMounted(async () => {
  syncRangeFromRoute();
  await fetchRecord(selectedRange.value);
});

watch(
  () => route.query,
  async () => {
    const previous = selectedRange.value;
    syncRangeFromRoute();
    if (previous !== selectedRange.value) {
      selectedPointIndex.value = null;
      await fetchRecord(selectedRange.value);
    }
  }
);

watch(selectedRange, () => {
  syncRouteFromRange();
});

const aggregateTrendPoints = (points: DailyTrendPoint[], range: TrendRangeKey): DailyTrendPoint[] => {
  const policy = TREND_RANGE_POLICY[range];
  const scoped = points.slice(-policy.rangeDays);
  const buckets: DailyTrendPoint[] = [];

  if (range === "6m") {
    const monthChunks: Array<{ monthKey: string; points: DailyTrendPoint[] }> = [];
    const monthIndexMap = new Map<string, number>();

    for (const point of scoped) {
      const monthKey = point.date.slice(0, 7);
      const index = monthIndexMap.get(monthKey);
      if (index === undefined) {
        monthIndexMap.set(monthKey, monthChunks.length);
        monthChunks.push({ monthKey, points: [point] });
      } else {
        monthChunks[index].points.push(point);
      }
    }

    for (const chunkInfo of monthChunks.slice(-policy.pointCount)) {
      const chunk = chunkInfo.points;
      const numericLevels = chunk
        .map((point) => (point.level === "missing" ? null : VALUE_BY_LEVEL[point.level]))
        .filter((value): value is number => value !== null);
      const averageLevel = numericLevels.length
        ? numericLevels.reduce((sum, value) => sum + value, 0) / numericLevels.length
        : null;

      const level: DailyTrendPoint["level"] =
        averageLevel === null ? "missing" : averageLevel >= 1.5 ? "stable" : averageLevel >= 0.5 ? "change" : "decline";

      buckets.push({
        date: `${chunkInfo.monthKey}-01`,
        level,
        flags: chunk.some((point) => point.flags.includes("ANOMALY")) ? ["ANOMALY"] : [],
        metrics: {
          interruptions: Math.round(
            chunk.reduce((sum, point) => sum + point.metrics.interruptions, 0) / chunk.length
          ),
          responseDelayPercent: Math.round(
            chunk.reduce((sum, point) => sum + point.metrics.responseDelayPercent, 0) / chunk.length
          ),
          participationGap: chunk.some((point) => point.metrics.participationGap),
        },
      });
    }

    return buckets;
  }

  for (let index = 0; index < scoped.length; index += policy.bucketSize) {
    const chunk = scoped.slice(index, index + policy.bucketSize);
    if (!chunk.length) continue;

    const numericLevels = chunk
      .map((point) => (point.level === "missing" ? null : VALUE_BY_LEVEL[point.level]))
      .filter((value): value is number => value !== null);
    const averageLevel = numericLevels.length
      ? numericLevels.reduce((sum, value) => sum + value, 0) / numericLevels.length
      : null;

    const level: DailyTrendPoint["level"] =
      averageLevel === null ? "missing" : averageLevel >= 1.5 ? "stable" : averageLevel >= 0.5 ? "change" : "decline";

    buckets.push({
      date: chunk[chunk.length - 1].date,
      level,
      flags: chunk.some((point) => point.flags.includes("ANOMALY")) ? ["ANOMALY"] : [],
      metrics: {
        interruptions: Math.round(
          chunk.reduce((sum, point) => sum + point.metrics.interruptions, 0) / chunk.length
        ),
        responseDelayPercent: Math.round(
          chunk.reduce((sum, point) => sum + point.metrics.responseDelayPercent, 0) / chunk.length
        ),
        participationGap: chunk.some((point) => point.metrics.participationGap),
      },
    });
  }

  return buckets.slice(-policy.pointCount);
};

const displayTrendPoints = computed<DailyTrendPoint[]>(() =>
  aggregateTrendPoints(record.value?.dailyTrendPoints ?? [], selectedRange.value)
);

watch(
  () => displayTrendPoints.value,
  (points) => {
    if (!points.length) {
      selectedPointIndex.value = null;
      return;
    }
    if (selectedPointIndex.value === null || selectedPointIndex.value >= points.length) {
      selectedPointIndex.value = points.length - 1;
    }
  },
  { immediate: true }
);

const handleRangeSelect = async (range: TrendRangeKey) => {
  if (selectedRange.value === range && record.value) return;
  selectedRange.value = range;
  selectedPointIndex.value = null;
  await fetchRecord(range);
};

const handlePointSelect = (index: number) => {
  selectedPointIndex.value = index;
};

const toMonthDay = (isoDate: string) => {
  const date = new Date(`${isoDate}T00:00:00`);
  if (Number.isNaN(date.getTime())) return isoDate;
  return `${date.getMonth() + 1}/${date.getDate()}`;
};

const statusStrengthMap: Record<string, ObservationSeverity> = {
  안정: "가벼움",
  변화: "주의",
  저하: "뚜렷함",
  미참여: "뚜렷함",
};

const trendHeadline = computed(() => {
  const status = record.value?.periodSummary.status;
  if (status === "저하") return "이번 기간은 저하 흐름";
  if (status === "변화") return "이번 기간은 변화 흐름";
  if (status === "미참여") return "이번 기간은 참여 공백 흐름";
  return "이번 기간은 안정 흐름";
});

const trendStrength = computed(
  () => statusStrengthMap[record.value?.periodSummary.status ?? "안정"] ?? ("가벼움" as ObservationSeverity)
);

const statusToneClass = computed(() => {
  const status = record.value?.periodSummary.status;
  if (status === "저하" || status === "미참여") return "danger";
  if (status === "변화") return "alert";
  return "stable";
});

const trendValues = computed<Array<number | null>>(() => {
  return displayTrendPoints.value.map((point) =>
    point.level === "missing" ? null : VALUE_BY_LEVEL[point.level]
  );
});

const trendStates = computed(() => displayTrendPoints.value.map((point) => point.level));
const trendDates = computed(() => displayTrendPoints.value.map((point) => point.date));
const trendLabels = computed(() => trendDates.value.map((date) => toMonthDay(date)));
const highlightIndices = computed(() =>
  displayTrendPoints.value
    .map((point, index) => (point.flags.includes("ANOMALY") ? index : -1))
    .filter((index) => index >= 0)
);

const selectedDay = computed(() => {
  const points = displayTrendPoints.value;
  if (selectedPointIndex.value === null) return null;
  return points[selectedPointIndex.value] ?? null;
});

const selectedDayDetail = computed(() => {
  if (!selectedDay.value) return null;
  const point = selectedDay.value;
  const evidence = [`중단 ${point.metrics.interruptions}회`, `반응지연 +${point.metrics.responseDelayPercent}%`];
  if (point.metrics.participationGap) evidence.push("미측정 1일");

  return {
    dateText: toMonthDay(point.date),
    levelText: LEVEL_TEXT[point.level],
    level: point.level,
    evidenceText: evidence.join(", "),
    interruptions: point.metrics.interruptions,
    responseDelayPercent: point.metrics.responseDelayPercent,
    participationGap: point.metrics.participationGap,
  };
});

const quickStats = computed(() => record.value?.periodSummary.quickStats.slice(0, 3) ?? []);
const dateRangeLabel = computed(() => record.value?.periodSummary.dateRangeLabel ?? "-");

const observationMap = computed(() => {
  const map = new Map<ObservationDomain, ObservationItem>();
  for (const item of record.value?.observationItems ?? []) {
    map.set(item.domain, item);
  }
  return map;
});

const createFallbackObservation = (domain: ObservationDomain): ObservationItem => ({
  domain,
  severity: "가벼움",
  title: `${DOMAIN_LABEL[domain]} 변화 관찰`,
  deltaMetrics: "지난 7일 0회 (이전 7일 대비 +0)",
  evidenceLogs: [],
  actions: [],
});

const observationCards = computed<ObservationItem[]>(() =>
  DOMAIN_ORDER.map((domain) => observationMap.value.get(domain) ?? createFallbackObservation(domain))
);

const notableChanges = computed(() => (record.value?.notableChanges ?? []).slice(0, 2));

const openInterpretationSheet = () => {
  interpretationSheetOpen.value = true;
  compareSectionOpen.value = false;
  rawLogSectionOpen.value = false;
};

const closeInterpretationSheet = () => {
  interpretationSheetOpen.value = false;
};

const toggleCompareSection = () => {
  compareSectionOpen.value = !compareSectionOpen.value;
};

const toggleRawLogSection = () => {
  rawLogSectionOpen.value = !rawLogSectionOpen.value;
};
</script>

<template>
  <div class="history-container">
    <div v-if="loading && !record" class="loading">
      <div class="spinner"></div>
    </div>

    <template v-else-if="record">
      <section class="card period-tabs">
        <div class="tabs-row" role="group" aria-label="관찰 기간 선택">
          <button
            v-for="option in TREND_RANGE_OPTIONS"
            :key="option.key"
            type="button"
            class="period-tab"
            :class="{ active: selectedRange === option.key }"
            :aria-pressed="selectedRange === option.key"
            @click="handleRangeSelect(option.key)"
          >
            {{ option.label }}
          </button>
        </div>
        <p class="date-range-label">{{ dateRangeLabel }}</p>
      </section>

      <section class="card">
        <header class="trend-head">
          <h3>기간 추세</h3>
          <span class="status-badge" :class="statusToneClass">{{ record.periodSummary.status }}</span>
        </header>
        <p class="trend-evidence">
          {{ record.periodSummary.evidenceMetrics }}
          <span class="strength-chip">{{ trendStrength }}</span>
        </p>
        <p class="trend-headline">{{ trendHeadline }}</p>

        <div class="quick-stats">
          <span v-for="stat in quickStats" :key="stat" class="quick-stat-chip">{{ stat }}</span>
        </div>

        <div class="chart-legend-row" aria-label="차트 범례">
          <span class="legend-item"><i class="dot"></i>상태점</span>
          <span class="legend-item"><i class="ring"></i>선택됨</span>
          <span class="legend-item danger"><i class="square"></i>미측정</span>
        </div>

        <div class="trend-chart-viewport">
          <div class="trend-chart-canvas">
            <WeeklyChart
              :data="trendValues"
              :states="trendStates"
              :dates="trendDates"
              :labels="trendLabels"
              :highlights="highlightIndices"
              :active-index="selectedPointIndex"
              :padding-left-px="66"
              :padding-right-px="28"
              :y-state-labels="['안정', '변화', '저하', '미측정']"
              @point-click="handlePointSelect"
            />
          </div>
        </div>

        <section v-if="selectedDayDetail" class="selected-detail-card">
          <header class="selected-detail-head">
            <span class="selected-date-chip">{{ selectedDayDetail.dateText }}</span>
            <span class="selected-level-chip" :class="selectedDayDetail.level">
              {{ selectedDayDetail.levelText }}
            </span>
          </header>
          <p class="selected-detail-text">근거: {{ selectedDayDetail.evidenceText }}</p>
          <div class="selected-detail-metrics">
            <span class="detail-chip">중단 {{ selectedDayDetail.interruptions }}회</span>
            <span class="detail-chip">반응지연 +{{ selectedDayDetail.responseDelayPercent }}%</span>
            <span v-if="selectedDayDetail.participationGap" class="detail-chip danger">미측정</span>
          </div>
        </section>

        <button type="button" class="cta-button" @click="openInterpretationSheet">차트 해석 보기</button>
      </section>

      <section class="card">
        <h3>관찰 포인트</h3>
        <div class="observation-grid">
          <article
            v-for="item in observationCards"
            :key="item.domain"
            class="observation-card"
          >
            <header class="observation-head">
              <span class="domain-tag">{{ DOMAIN_LABEL[item.domain] }}</span>
              <span class="severity-badge">{{ item.severity }}</span>
            </header>
            <p class="observation-title">{{ item.title }}</p>
            <p class="observation-metrics">{{ item.deltaMetrics }}</p>

            <div class="observation-inline">
              <p class="inline-title">근거 로그</p>
              <ul class="inline-list">
                <li v-for="log in item.evidenceLogs.slice(0, 3)" :key="`${item.domain}-${log.date}-${log.detail}`">
                  {{ toMonthDay(log.date) }} · {{ log.detail }}
                </li>
                <li v-if="!item.evidenceLogs.length" class="inline-empty">기록된 로그가 없습니다.</li>
              </ul>
            </div>

            <div class="observation-inline">
              <p class="inline-title">권장 행동</p>
              <ul class="inline-list">
                <li v-for="action in item.actions.slice(0, 2)" :key="`${item.domain}-${action}`">{{ action }}</li>
                <li v-if="!item.actions.length" class="inline-empty">표시할 권장 행동이 없습니다.</li>
              </ul>
            </div>
          </article>
        </div>
      </section>

      <section class="card">
        <h3>눈여겨볼 변화</h3>
        <p class="section-desc">최근 24~48시간의 변화</p>
        <div class="notable-grid">
          <article v-for="item in notableChanges" :key="`${item.domain}-${item.whenLabel}-${item.title}`" class="notable-card">
            <header class="notable-head">
              <span class="domain-tag">{{ DOMAIN_LABEL[item.domain] }}</span>
              <span class="when-label">{{ item.whenLabel }}</span>
            </header>
            <p class="notable-title">{{ item.title }}</p>
            <p class="notable-action">{{ item.actionTip }}</p>
          </article>
        </div>
      </section>
    </template>

    <p v-if="error" class="error-text">{{ error }}</p>

    <teleport to="body">
      <div v-if="interpretationSheetOpen && record" class="sheet-overlay" @click.self="closeInterpretationSheet">
        <section class="sheet-card" role="dialog" aria-modal="true" aria-label="차트 해석">
          <header class="sheet-header">
            <h4>차트 해석</h4>
            <button type="button" class="sheet-close" @click="closeInterpretationSheet">닫기</button>
          </header>

          <section class="sheet-section open">
            <h5>요약</h5>
            <p><strong>상태:</strong> {{ record.periodSummary.status }}</p>
            <p><strong>근거:</strong> {{ record.periodSummary.evidenceMetrics }}</p>
            <p><strong>권장 행동:</strong> {{ record.periodSummary.recommendedAction }}</p>
          </section>

          <section class="sheet-section">
            <button type="button" class="section-toggle" @click="toggleCompareSection">
              기간 비교 수치 {{ compareSectionOpen ? "접기" : "펼치기" }}
            </button>
            <div v-if="compareSectionOpen" class="compare-table">
              <div class="row head">
                <span>항목</span>
                <span>이번 기간</span>
                <span>이전 기간</span>
              </div>
              <div v-for="row in record.periodSummary.comparisonRows.slice(0, 3)" :key="row.label" class="row">
                <span>{{ row.label }}</span>
                <span>{{ row.current }}</span>
                <span>{{ row.previous }}</span>
              </div>
            </div>
          </section>

          <section class="sheet-section">
            <button type="button" class="section-toggle" @click="toggleRawLogSection">
              원시 로그 {{ rawLogSectionOpen ? "접기" : "펼치기" }}
            </button>
            <ul v-if="rawLogSectionOpen" class="raw-log-list">
              <li v-for="log in record.rawLogs" :key="`${log.date}-${log.detail}`">
                {{ toMonthDay(log.date) }} · {{ log.detail }}
              </li>
            </ul>
          </section>
        </section>
      </div>
    </teleport>

  </div>
</template>

<style scoped>
.history-container {
  --card-surface: #f7f9fa;
  --card-radius: 20px;
  --card-gap: 16px;
  --card-elevation-main:
    0 10px 22px rgba(126, 140, 154, 0.18),
    0 3px 8px rgba(126, 140, 154, 0.11),
    0 1px 3px rgba(126, 140, 154, 0.06);
  --card-elevation-sub:
    0 8px 16px rgba(126, 140, 154, 0.14),
    0 2px 6px rgba(126, 140, 154, 0.1);
  display: grid;
  gap: var(--card-gap);
  width: 100%;
  padding-bottom: calc(env(safe-area-inset-bottom, 0px) + 96px);
}

.card {
  border-radius: var(--card-radius);
  box-shadow: var(--card-elevation-main);
  background: var(--card-surface);
  padding: 16px 16px 14px;
  display: grid;
  gap: 12px;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 220px;
}

.spinner {
  width: 38px;
  height: 38px;
  border: 4px solid #d9e1e6;
  border-top-color: #4aa9aa;
  border-radius: 999px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.period-tabs {
  gap: 8px;
  padding-top: 10px;
  padding-bottom: 9px;
}

.tabs-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.period-tab {
  border: 1px solid #cad7e0;
  background: #ffffff;
  border-radius: 12px;
  padding: 7px 7px;
  font-size: clamp(14px, 1.2vw, 17px);
  font-weight: 800;
  color: #57646d;
  cursor: pointer;
  transition: background-color 0.16s ease, color 0.16s ease, border-color 0.16s ease;
}

.period-tab.active {
  background: #cfecec;
  color: #1f5a5b;
  font-weight: 700;
  border-color: #7ec5c6;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.date-range-label {
  margin: 0;
  font-size: clamp(14px, 1.1vw, 16px);
  font-weight: 600;
  color: #5f6f79;
}

h3 {
  margin: 0;
  font-size: clamp(23px, 2.2vw, 30px);
  font-weight: 900;
  color: #2e2e2e;
}

.trend-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.status-badge {
  border-radius: 999px;
  padding: 8px 14px;
  font-size: clamp(14px, 1.1vw, 18px);
  font-weight: 900;
  line-height: 1;
}

.status-badge.stable {
  background: rgba(76, 183, 183, 0.16);
  color: #1f5f5f;
}

.status-badge.alert {
  background: rgba(255, 183, 77, 0.24);
  color: #c77715;
}

.status-badge.danger {
  background: rgba(255, 138, 128, 0.22);
  color: #b65048;
}

.trend-evidence {
  margin: 0;
  font-size: clamp(17px, 1.7vw, 22px);
  font-weight: 800;
  color: #344652;
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.strength-chip {
  border-radius: 999px;
  padding: 4px 10px;
  background: #fff2d8;
  color: #9e6824;
  font-size: clamp(12px, 1vw, 14px);
  font-weight: 800;
}

.trend-headline {
  margin: 0;
  font-size: clamp(15px, 1.3vw, 18px);
  font-weight: 800;
  color: #4a5c68;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.quick-stats {
  display: flex;
  flex-wrap: wrap;
  column-gap: 8px;
  row-gap: 8px;
  margin: 0;
}

.quick-stat-chip {
  border-radius: 999px;
  border: 1px solid #cfdce6;
  background: #f8fbfb;
  color: #4e5d67;
  font-size: clamp(13px, 1.1vw, 15px);
  font-weight: 800;
  padding: 5px 10px;
  min-width: 98px;
  text-align: center;
}

.chart-legend-row {
  display: inline-flex;
  justify-self: start;
  flex-wrap: wrap;
  gap: 9px;
  border-radius: 999px;
  background: rgba(247, 249, 250, 0.96);
  border: 1px solid #d4e2ea;
  padding: 6px 10px;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: clamp(12px, 0.9vw, 14px);
  font-weight: 700;
  color: #4e5e68;
}

.legend-item.danger {
  color: #b04e47;
}

.dot,
.ring,
.square {
  width: 10px;
  height: 10px;
  display: inline-block;
}

.dot {
  border-radius: 999px;
  background: #4cb7b7;
}

.ring {
  border-radius: 999px;
  border: 2.4px solid #35596e;
}

.square {
  border: 2px solid #bd554e;
  background: #ffb8b0;
}

.trend-chart-viewport {
  width: 100%;
  overflow: hidden;
}

.trend-chart-canvas {
  width: min(100%, 760px);
  margin: 0 auto;
}

.selected-detail-card {
  border-radius: 14px;
  background: #f8fbfb;
  box-shadow: var(--card-elevation-sub);
  padding: 12px 14px;
  display: grid;
  gap: 8px;
}

.selected-detail-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.selected-date-chip,
.selected-level-chip {
  border-radius: 999px;
  padding: 5px 10px;
  font-size: clamp(12px, 1vw, 14px);
  font-weight: 800;
}

.selected-date-chip {
  background: #eaf1f4;
  color: #4f5f69;
}

.selected-level-chip.stable {
  background: rgba(76, 183, 183, 0.16);
  color: #1f5f5f;
}

.selected-level-chip.change {
  background: rgba(255, 183, 77, 0.24);
  color: #c77715;
}

.selected-level-chip.decline {
  background: rgba(255, 138, 128, 0.24);
  color: #b65048;
}

.selected-level-chip.missing {
  background: rgba(185, 64, 58, 0.2);
  color: #a43a34;
}

.selected-detail-text {
  margin: 0;
  font-size: clamp(15px, 1.2vw, 18px);
  font-weight: 800;
  color: #3f4f59;
}

.selected-detail-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.detail-chip {
  border-radius: 999px;
  border: 1px solid #cad7e0;
  background: #ffffff;
  color: #4f5f69;
  padding: 4px 9px;
  font-size: clamp(12px, 1vw, 14px);
  font-weight: 800;
}

.detail-chip.danger {
  border-color: #c6635d;
  background: #ffe8e5;
  color: #a43a34;
}

.cta-button {
  border: none;
  border-radius: 14px;
  background: #4cb7b7;
  color: #ffffff;
  font-size: clamp(16px, 1.4vw, 20px);
  font-weight: 900;
  padding: 12px 18px;
  justify-self: start;
  cursor: pointer;
  box-shadow: 0 8px 16px rgba(76, 183, 183, 0.28);
}

.observation-grid,
.notable-grid {
  display: grid;
  gap: 12px;
}

.observation-card,
.notable-card {
  border-radius: var(--card-radius);
  box-shadow: var(--card-elevation-sub);
  background: #f8fbfb;
  padding: 14px;
  display: grid;
  gap: 10px;
}

.observation-head,
.notable-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.domain-tag,
.severity-badge,
.when-label {
  border-radius: 999px;
  padding: 4px 10px;
  font-size: clamp(12px, 1vw, 14px);
  font-weight: 800;
}

.domain-tag {
  background: #eaf1f4;
  color: #56626b;
}

.severity-badge {
  background: rgba(255, 183, 77, 0.2);
  color: #a26e24;
}

.when-label {
  background: rgba(255, 183, 77, 0.2);
  color: #9a712f;
}

.observation-title,
.notable-title {
  margin: 0;
  font-size: clamp(19px, 1.8vw, 24px);
  font-weight: 900;
  color: #253949;
  line-height: 1.35;
}

.observation-metrics,
.section-desc,
.notable-action {
  margin: 0;
  font-size: clamp(15px, 1.2vw, 18px);
  font-weight: 700;
  color: #4f616c;
  line-height: 1.45;
}

.observation-inline {
  display: grid;
  gap: 4px;
  border-top: 1px solid #dde7ee;
  padding-top: 6px;
}

.inline-title {
  margin: 0;
  font-size: clamp(13px, 1vw, 15px);
  font-weight: 800;
  color: #4d5d67;
}

.inline-list {
  margin: 0;
  padding-left: 16px;
  display: grid;
  gap: 4px;
}

.inline-list li {
  font-size: clamp(13px, 1vw, 15px);
  font-weight: 700;
  color: #5c6b74;
  line-height: 1.45;
  white-space: normal;
  overflow: visible;
  text-overflow: clip;
  word-break: keep-all;
  overflow-wrap: anywhere;
}

.inline-empty {
  list-style: none;
  margin-left: -16px;
  color: #78868f;
}

.notable-action {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.error-text {
  margin: 0;
  border-radius: 12px;
  padding: 10px 12px;
  font-size: clamp(14px, 1.1vw, 16px);
  font-weight: 600;
  color: #a94944;
  background: #ffeceb;
}

.sheet-overlay {
  position: fixed;
  inset: 0;
  background: rgba(24, 32, 40, 0.48);
  z-index: 500;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.sheet-card {
  width: min(620px, 100%);
  max-height: min(78vh, 680px);
  overflow: auto;
  border-top-left-radius: 20px;
  border-top-right-radius: 20px;
  box-shadow: 0 -6px 18px rgba(24, 32, 40, 0.2);
  background: var(--card-surface);
  padding: 16px;
  display: grid;
  gap: 12px;
}

.sheet-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.sheet-header h4 {
  margin: 0;
  font-size: clamp(20px, 1.8vw, 26px);
  font-weight: 900;
  color: #2e2e2e;
}

.sheet-close,
.section-toggle {
  border: 1px solid #d7e3ea;
  border-radius: 8px;
  background: #ffffff;
  color: #334954;
  font-size: clamp(13px, 1vw, 15px);
  font-weight: 700;
  padding: 8px 12px;
  cursor: pointer;
}

.sheet-section {
  border: 1px solid #e0e8ee;
  border-radius: 12px;
  background: #ffffff;
  padding: 12px;
  display: grid;
  gap: 8px;
}

.sheet-section h5 {
  margin: 0;
  font-size: clamp(17px, 1.4vw, 20px);
  font-weight: 800;
  color: #2d3f49;
}

.sheet-section p {
  margin: 0;
  font-size: clamp(14px, 1.1vw, 16px);
  font-weight: 600;
  color: #4d5e68;
}

.compare-table {
  display: grid;
  gap: 6px;
}

.row {
  display: grid;
  grid-template-columns: 1.1fr 1fr 1fr;
  gap: 8px;
  font-size: clamp(14px, 1.1vw, 16px);
  font-weight: 600;
  color: #4d5e68;
}

.row.head {
  font-weight: 700;
  color: #334954;
}

.raw-log-list {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 6px;
}

.raw-log-list li {
  font-size: clamp(14px, 1.1vw, 16px);
  font-weight: 600;
  color: #4f5f69;
}

@media (max-width: 560px) {
  .tabs-row {
    gap: 6px;
  }

  .period-tab {
    font-size: 14px;
    padding: 7px 4px;
  }
}
</style>
