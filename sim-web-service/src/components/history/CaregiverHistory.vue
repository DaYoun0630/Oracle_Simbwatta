<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import WeeklyChart from "../WeeklyChart.vue";
import { useWeeklyTrend } from "@/composables/useWeeklyTrend";
import { buildTrendBuckets } from "@/composables/useTrendBuckets";
import {
  TREND_RANGE_OPTIONS,
  buildTrendQueryForRange,
  getTrendRangeHeading,
  type TrendRangeKey,
} from "@/composables/useTrendRange";
import {
  buildCaregiverAlertBundle,
  formatBucketRangeLabel,
  getAlertKindLabel,
  getAlertToneLabel,
  getBucketStateText,
} from "@/composables/useCaregiverAlerts";
import type { AlertAxis } from "@/composables/caregiverAlertTypes";

type HistoryTab = "monitoring" | "summary";

const TAB_VALUES: HistoryTab[] = ["monitoring", "summary"];
const AXIS_VALUES: AlertAxis[] = ["participation", "training", "speech"];
const AXIS_ORDER: AlertAxis[] = ["participation", "training", "speech"];

const isTrendRangeKey = (value: unknown): value is TrendRangeKey =>
  typeof value === "string" && TREND_RANGE_OPTIONS.some((option) => option.key === value);
const isHistoryTab = (value: unknown): value is HistoryTab =>
  typeof value === "string" && TAB_VALUES.includes(value as HistoryTab);
const isAlertAxis = (value: unknown): value is AlertAxis =>
  typeof value === "string" && AXIS_VALUES.includes(value as AlertAxis);

const route = useRoute();
const router = useRouter();
const { trend, loading: trendLoading, error: trendError, fetchWeeklyTrend } = useWeeklyTrend();

const selectedRange = ref<TrendRangeKey>("7d");
const activeTab = ref<HistoryTab>("summary");
const focusedAxis = ref<AlertAxis | null>(null);
const selectedIndex = ref<number | null>(null);
const isBucketDrawerOpen = ref(false);

const fetchTrendByRange = async (rangeKey: TrendRangeKey = selectedRange.value) =>
  fetchWeeklyTrend(buildTrendQueryForRange(rangeKey));

const syncStateFromRoute = (fetchOnRangeChange: boolean) => {
  const periodQuery = route.query.period;
  const tabQuery = route.query.tab;
  const axisQuery = route.query.axis;

  const nextRange = isTrendRangeKey(periodQuery) ? periodQuery : "7d";
  const nextTab = isHistoryTab(tabQuery) ? tabQuery : "summary";
  const nextAxis = isAlertAxis(axisQuery) ? axisQuery : null;

  const rangeChanged = selectedRange.value !== nextRange;
  selectedRange.value = nextRange;
  activeTab.value = nextTab;
  focusedAxis.value = nextAxis;

  if (fetchOnRangeChange && rangeChanged) {
    void fetchTrendByRange(nextRange);
  }
};

const syncRouteFromState = () => {
  const nextQuery = {
    ...route.query,
    tab: activeTab.value,
    period: selectedRange.value,
  } as Record<string, string>;

  if (focusedAxis.value) {
    nextQuery.axis = focusedAxis.value;
  } else {
    delete nextQuery.axis;
  }

  const currentTab = typeof route.query.tab === "string" ? route.query.tab : "";
  const currentPeriod = typeof route.query.period === "string" ? route.query.period : "";
  const currentAxis = typeof route.query.axis === "string" ? route.query.axis : "";
  const nextAxis = nextQuery.axis ?? "";

  if (currentTab === nextQuery.tab && currentPeriod === nextQuery.period && currentAxis === nextAxis) {
    return;
  }

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

watch([selectedRange, activeTab, focusedAxis], () => {
  syncRouteFromState();
});

const handleRangeSelect = (rangeKey: TrendRangeKey) => {
  if (selectedRange.value === rangeKey && trend.value) return;
  selectedRange.value = rangeKey;
  selectedIndex.value = null;
  void fetchTrendByRange(rangeKey);
};

const handleTabSelect = (tab: HistoryTab) => {
  if (activeTab.value === tab) return;
  activeTab.value = tab;
};

const handleAxisFocus = (axis: AlertAxis) => {
  focusedAxis.value = focusedAxis.value === axis ? null : axis;
};

const bucketedTrend = computed(() => buildTrendBuckets(trend.value?.points ?? [], selectedRange.value));
const alertBundle = computed(() => buildCaregiverAlertBundle(selectedRange.value, bucketedTrend.value));

const summaryAlerts = computed(() => {
  const map = new Map(alertBundle.value.summaryAlerts.map((alert) => [alert.axis, alert]));
  return AXIS_ORDER.map((axis) => map.get(axis)).filter((alert) => Boolean(alert));
});

const monitoringAlerts = computed(() => alertBundle.value.monitoringAlerts);
const monitoringStatusText = computed(() =>
  monitoringAlerts.value.length
    ? "급격한 변화가 감지된 축을 우선으로 보여줍니다."
    : "현재는 급격한 변화 알림이 감지되지 않았습니다."
);

const trendHeading = computed(() => `${getTrendRangeHeading(selectedRange.value)} 관찰 흐름`);
const rangeLabel = computed(() => alertBundle.value.rangeLabel);
const isInitialLoading = computed(() => trendLoading.value && !trend.value);

const trendValues = computed<Array<number | null>>(() => bucketedTrend.value.values);
const trendLabels = computed(() => bucketedTrend.value.labels);
const trendDates = computed(() => bucketedTrend.value.dates);
const trendStates = computed(() => bucketedTrend.value.states);
const highlightIndices = computed(() => bucketedTrend.value.highlights);

watch(
  () => bucketedTrend.value.buckets,
  (buckets) => {
    if (!buckets.length) {
      selectedIndex.value = null;
      return;
    }
    if (selectedIndex.value === null || selectedIndex.value < 0 || selectedIndex.value >= buckets.length) {
      selectedIndex.value = buckets[buckets.length - 1].index;
    }
  },
  { immediate: true }
);

const handlePointClick = (index: number) => {
  selectedIndex.value = index;
};

const selectedBucket = computed(() =>
  bucketedTrend.value.buckets.find((bucket) => bucket.index === selectedIndex.value) ?? null
);

const selectedBucketLabel = computed(() =>
  selectedBucket.value ? formatBucketRangeLabel(selectedBucket.value) : rangeLabel.value
);

const selectedBucketStateText = computed(() =>
  selectedBucket.value ? getBucketStateText(selectedBucket.value.state) : "관찰 구간을 선택해 흐름을 확인해보세요."
);

const bucketHistoryItems = computed(() =>
  bucketedTrend.value.buckets.map((bucket) => ({
    id: `${bucket.index}-${bucket.endDate}`,
    axisLabel: formatBucketRangeLabel(bucket),
    stateText: getBucketStateText(bucket.state),
    hasAnomaly: bucket.hasAnomaly,
    hasMissing: bucket.missingDays > 0 || bucket.state === "missing",
  }))
);

const openBucketDrawer = () => {
  isBucketDrawerOpen.value = true;
};

const closeBucketDrawer = () => {
  isBucketDrawerOpen.value = false;
};
</script>

<template>
  <div class="history-container">
    <div v-if="isInitialLoading" class="loading">
      <div class="spinner"></div>
    </div>

    <template v-else>
      <section class="tab-card">
        <button
          type="button"
          class="tab-button"
          :class="{ active: activeTab === 'summary' }"
          @click="handleTabSelect('summary')"
        >
          기간 요약
        </button>
        <button
          type="button"
          class="tab-button"
          :class="{ active: activeTab === 'monitoring' }"
          @click="handleTabSelect('monitoring')"
        >
          모니터링
        </button>
      </section>

      <section v-if="activeTab === 'summary'" class="panel-card">
        <div class="panel-header">
          <div>
            <h3>{{ trendHeading }}</h3>
            <p class="panel-sub">기간별 평균 관찰을 기반으로 참여, 훈련, 발화 흐름을 요약합니다.</p>
          </div>
          <span class="range-chip">{{ rangeLabel }}</span>
        </div>

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

        <WeeklyChart
          :data="trendValues"
          :labels="trendLabels"
          :dates="trendDates"
          :states="trendStates"
          :highlights="highlightIndices"
          :activeIndex="selectedIndex"
          :y-state-labels="['안정', '변화', '저하', '미참여']"
          @point-click="handlePointClick"
        />

        <p class="chart-note">{{ selectedBucketLabel }}</p>
        <p class="chart-note">{{ selectedBucketStateText }}</p>
        <p v-if="trendError" class="chart-note error">{{ trendError }}</p>

        <div class="summary-alert-grid">
          <article
            v-for="alert in summaryAlerts"
            :key="alert.id"
            class="summary-alert-card"
            :class="{ focused: focusedAxis === alert.axis }"
            @click="handleAxisFocus(alert.axis)"
          >
            <div class="summary-alert-head">
              <span class="axis-tag">{{ alert.tagLabel }}</span>
              <span class="tone-tag">{{ getAlertToneLabel(alert.tone) }}</span>
            </div>
            <p class="summary-alert-title">{{ alert.titleLine }}</p>
            <p class="summary-alert-action">{{ alert.actionLine }}</p>
          </article>
        </div>

        <button type="button" class="drawer-open-button" @click="openBucketDrawer">
          지난 기간 흐름 더 보기
        </button>
      </section>

      <section v-else class="panel-card">
        <div class="panel-header">
          <div>
            <h3>급격 변화 모니터링</h3>
            <p class="panel-sub">{{ monitoringStatusText }}</p>
          </div>
          <span class="kind-chip">실시간 감지</span>
        </div>

        <p class="external-note">외부 발송은 아직 연결하지 않고, 앱 내부 알림만 표시하고 있습니다.</p>
        <p class="range-note">{{ rangeLabel }}</p>

        <div v-if="monitoringAlerts.length" class="monitoring-list">
          <article
            v-for="alert in monitoringAlerts"
            :key="alert.id"
            class="monitoring-item"
            :class="{ focused: focusedAxis === alert.axis }"
            @click="handleAxisFocus(alert.axis)"
          >
            <div class="monitoring-head">
              <span class="kind-tag">{{ getAlertKindLabel(alert.kind) }}</span>
              <span class="axis-tag">{{ alert.tagLabel }}</span>
              <span class="tone-tag">{{ getAlertToneLabel(alert.tone) }}</span>
            </div>
            <p class="monitoring-title">{{ alert.titleLine }}</p>
            <p class="monitoring-action">{{ alert.actionLine }}</p>
          </article>
        </div>
        <p v-else class="monitoring-empty">
          지금은 급격한 변화가 감지되지 않았습니다. 기간 요약 탭에서 장기 흐름을 함께 확인해보세요.
        </p>
      </section>
    </template>

    <teleport to="body">
      <div v-if="isBucketDrawerOpen" class="drawer-overlay" @click.self="closeBucketDrawer">
        <section class="bucket-drawer" role="dialog" aria-modal="true" aria-label="지난 기간 흐름">
          <div class="drawer-header">
            <h4>지난 기간 흐름</h4>
            <button type="button" class="drawer-close" @click="closeBucketDrawer">닫기</button>
          </div>
          <p class="drawer-sub">각 버킷은 기간 평균 관찰을 의미합니다.</p>
          <div class="bucket-list">
            <article v-for="item in bucketHistoryItems" :key="item.id" class="bucket-item">
              <p class="bucket-range">{{ item.axisLabel }}</p>
              <p class="bucket-state">{{ item.stateText }}</p>
              <div class="bucket-flags">
                <span v-if="item.hasAnomaly" class="bucket-flag">변화 감지</span>
                <span v-if="item.hasMissing" class="bucket-flag">기록 공백</span>
              </div>
            </article>
          </div>
        </section>
      </div>
    </teleport>
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
  gap: 18px;
  width: 100%;
  max-width: 100%;
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

.tab-card,
.panel-card {
  background: var(--card-surface);
  border-radius: 22px;
  box-shadow: var(--card-elevation-main);
}

.tab-card {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  padding: 10px;
}

.tab-button {
  border: none;
  border-radius: 999px;
  padding: 8px 12px;
  background: #eef3f5;
  color: #56636c;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  box-shadow: inset 2px 2px 4px rgba(129, 142, 153, 0.2), inset -2px -2px 4px rgba(255, 255, 255, 0.95);
  transition: transform 0.18s ease, box-shadow 0.18s ease, background-color 0.18s ease, color 0.18s ease;
}

.tab-button:hover {
  transform: translateY(-1px);
}

.tab-button.active {
  background: #4cb7b7;
  color: #ffffff;
  box-shadow: 0 6px 12px rgba(76, 183, 183, 0.25);
}

.panel-card {
  padding: 18px 16px;
  display: grid;
  gap: 12px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: flex-start;
}

.panel-header h3 {
  margin: 0;
  font-size: 21px;
  font-weight: 900;
  color: #2e2e2e;
}

.panel-sub {
  margin: 6px 0 0;
  font-size: 15px;
  color: #5a666f;
  line-height: 1.5;
}

.range-chip,
.kind-chip {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 7px 11px;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}

.range-chip {
  color: #4f6b7a;
  background: #eef3f5;
}

.kind-chip {
  color: #2e8f8f;
  background: rgba(76, 183, 183, 0.16);
}

.range-controls {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 8px;
}

.range-button {
  border: none;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 14px;
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

.chart-note {
  margin: 0;
  font-size: 14px;
  line-height: 1.45;
  color: #66737c;
}

.chart-note.error {
  color: #d87a71;
}

.summary-alert-grid {
  display: grid;
  gap: 10px;
}

.summary-alert-card {
  border: none;
  border-radius: 16px;
  background: #f8fbfb;
  box-shadow: var(--card-elevation-sub);
  padding: 12px 13px;
  display: grid;
  gap: 8px;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.summary-alert-card:hover {
  transform: translateY(-1px);
  box-shadow: var(--card-elevation-hover);
}

.summary-alert-card.focused {
  box-shadow:
    0 0 0 2px rgba(76, 183, 183, 0.2),
    var(--card-elevation-sub);
}

.summary-alert-head,
.monitoring-head {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  align-items: center;
}

.axis-tag,
.tone-tag,
.kind-tag {
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

.tone-tag {
  background: rgba(130, 130, 130, 0.14);
  color: #616b72;
}

.kind-tag {
  background: rgba(255, 183, 77, 0.2);
  color: #b57d2d;
}

.summary-alert-title,
.monitoring-title {
  margin: 0;
  font-size: 16px;
  font-weight: 900;
  line-height: 1.45;
  color: #30363a;
}

.summary-alert-action,
.monitoring-action {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
  color: #4f5d66;
}

.drawer-open-button {
  border: none;
  border-radius: 999px;
  justify-self: start;
  background: #e6f2f1;
  color: #2e8f8f;
  font-size: 13px;
  font-weight: 800;
  padding: 8px 13px;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, background-color 0.18s ease;
}

.drawer-open-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 12px rgba(76, 183, 183, 0.2);
}

.external-note,
.range-note {
  margin: 0;
  font-size: 14px;
  line-height: 1.45;
  color: #66737c;
}

.monitoring-list {
  display: grid;
  gap: 10px;
}

.monitoring-item {
  border-radius: 16px;
  padding: 12px 13px;
  background: #f8fbfb;
  box-shadow: var(--card-elevation-sub);
  display: grid;
  gap: 8px;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.monitoring-item:hover {
  transform: translateY(-1px);
  box-shadow: var(--card-elevation-hover);
}

.monitoring-item.focused {
  box-shadow:
    0 0 0 2px rgba(255, 183, 77, 0.25),
    var(--card-elevation-sub);
}

.monitoring-empty {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
  color: #66737c;
}

.drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(22, 32, 40, 0.45);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  z-index: 500;
}

.bucket-drawer {
  width: min(560px, 100%);
  max-height: min(72vh, 620px);
  background: #f7f9fa;
  border-top-left-radius: 20px;
  border-top-right-radius: 20px;
  box-shadow: 0 -6px 18px rgba(30, 45, 55, 0.22);
  padding: 14px 14px calc(20px + env(safe-area-inset-bottom, 0px));
  display: grid;
  gap: 10px;
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.drawer-header h4 {
  margin: 0;
  font-size: 18px;
  font-weight: 900;
  color: #2e2e2e;
}

.drawer-close {
  border: none;
  border-radius: 999px;
  background: #eaf1f4;
  color: #55626b;
  font-size: 12px;
  font-weight: 800;
  padding: 6px 10px;
  cursor: pointer;
  transition: transform 0.18s ease, background-color 0.18s ease;
}

.drawer-close:hover {
  transform: translateY(-1px);
  background: #e3ecef;
}

.drawer-sub {
  margin: 0;
  font-size: 13px;
  color: #66737c;
}

.bucket-list {
  max-height: min(58vh, 500px);
  overflow: auto;
  display: grid;
  gap: 9px;
  padding-right: 4px;
}

.bucket-item {
  border-radius: 14px;
  background: #f8fbfb;
  box-shadow: var(--card-elevation-sub);
  padding: 11px 12px;
  display: grid;
  gap: 6px;
}

.bucket-range {
  margin: 0;
  font-size: 13px;
  font-weight: 800;
  color: #5c6972;
}

.bucket-state {
  margin: 0;
  font-size: 14px;
  line-height: 1.45;
  color: #45525b;
}

.bucket-flags {
  display: flex;
  gap: 7px;
  flex-wrap: wrap;
}

.bucket-flag {
  border-radius: 999px;
  background: rgba(255, 183, 77, 0.2);
  color: #b57d2d;
  padding: 4px 9px;
  font-size: 11px;
  font-weight: 800;
}

@media (max-width: 560px) {
  .panel-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .panel-card {
    padding: 16px 14px;
  }

  .summary-alert-title,
  .monitoring-title {
    font-size: 15px;
  }
}
</style>
