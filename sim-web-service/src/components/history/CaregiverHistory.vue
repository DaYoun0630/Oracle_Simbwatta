<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useCaregiverData } from "@/composables/useCaregiverData";
import WeeklyChart from "../WeeklyChart.vue";

const { data, loading, fetchData } = useCaregiverData();

onMounted(() => {
  fetchData();
});

const dayNames = ["일", "월", "화", "수", "목", "금", "토"];

const dateItems = computed(() => {
  const items: { index: number; label: string; dateText: string; dayOffset: number }[] = [];
  const today = new Date();
  for (let i = 6; i >= 0; i -= 1) {
    const d = new Date();
    d.setDate(today.getDate() - i)
    items.push({
      index: items.length,
      label: dayNames[d.getDay()],
      dateText: d.toLocaleDateString("ko-KR", {
        month: "long",
        day: "numeric",
        weekday: "short",
      }),
      dayOffset: 6 - items.length,
    });
  }
  return items;
});

const lastSevenDays = computed(() => dateItems.value.map((item) => item.label));

const weeklyFlow = computed(() => data.value?.weeklyTrend?.scores ?? []);

const observations = computed(() => data.value?.weeklyObservations ?? []);

const observationsWithIndex = computed(() =>
  observations.value
    .map((item) => ({
      ...item,
      index: 6 - item.dayOffset,
      dateText: dateItems.value.find((d) => d.index === 6 - item.dayOffset)?.dateText ?? "",
    }))
    .filter((item) => item.index >= 0 && item.index <= 6)
);

const highlightIndices = computed(() => observationsWithIndex.value.map((item) => item.index));

const selectedIndex = ref<number | null>(null);

watch(highlightIndices, (list) => {
  if (!list.length) {
    selectedIndex.value = 6;
    return;
  }
  if (selectedIndex.value === null || !list.includes(selectedIndex.value)) {
    selectedIndex.value = list[0];
  }
}, { immediate: true });

const selectedObservation = computed(() =>
  observationsWithIndex.value.find((item) => item.index === selectedIndex.value) ?? null
);

const selectedDate = computed(() => {
  const item = dateItems.value.find((d) => d.index === selectedIndex.value);
  return item?.dateText ?? "";
});

const insightText = computed(() => {
  const count = observationsWithIndex.value.length;
  if (count === 0) {
    return "최근 7일 동안 발화 리듬이 안정적으로 유지되었습니다.";
  }
  return `최근 7일 중 ${count}일에서 발화 리듬 변화가 관찰되었습니다.`;
});

const handlePointClick = (index: number) => {
  selectedIndex.value = index;
};

const observationLabel = (type: string) => {
  if (type === "pause") return "대화 여유";
  if (type === "hesitation") return "흐름 정체";
  if (type === "encouragement") return "독려 필요";
  return "관찰";
};
</script>

<template>
  <div class="history-container">
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
    </div>

    <template v-else>
      <section class="trend-card">
        <div class="section-header">
          <span class="mint-dot"></span>
          <div>
            <h3>최근 7일 발화 흐름</h3>
            <p class="section-sub">평가 대신 리듬과 반응 속도를 관찰합니다.</p>
          </div>
        </div>

        <WeeklyChart
          :data="weeklyFlow"
          :labels="lastSevenDays"
          :highlights="highlightIndices"
          :activeIndex="selectedIndex"
          @point-click="handlePointClick"
        />

        <div class="legend">
          <div class="legend-item">
            <span class="legend-icon pause">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <rect x="6" y="5" width="4" height="14" rx="2" />
                <rect x="14" y="5" width="4" height="14" rx="2" />
              </svg>
            </span>
            <span>대화 여유</span>
          </div>
          <div class="legend-item">
            <span class="legend-icon hesitation">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M2 12c3-3 6-3 9 0s6 3 9 0" />
                <path d="M2 17c3-3 6-3 9 0s6 3 9 0" />
              </svg>
            </span>
            <span>흐름 정체</span>
          </div>
        </div>
      </section>

      <section class="insight-card">
        <h4>관찰 요약</h4>
        <p>{{ insightText }}</p>
      </section>

      <section class="log-card">
        <div class="log-header">
          <h4>관찰 로그</h4>
          <span class="date-chip">{{ selectedDate }}</span>
        </div>

        <div v-if="selectedObservation" class="log-detail">
          <div class="log-icon" :class="selectedObservation.type">
            <svg v-if="selectedObservation.type === 'pause'" viewBox="0 0 48 48" aria-hidden="true">
              <rect x="14" y="12" width="8" height="24" rx="3" />
              <rect x="26" y="12" width="8" height="24" rx="3" />
            </svg>
            <svg v-else-if="selectedObservation.type === 'hesitation'" viewBox="0 0 48 48" aria-hidden="true">
              <path d="M8 26c6-6 12-6 18 0s12 6 18 0" />
              <path d="M8 34c6-6 12-6 18 0s12 6 18 0" />
            </svg>
            <svg v-else-if="selectedObservation.type === 'encouragement'" viewBox="0 0 48 48" aria-hidden="true">
              <circle cx="24" cy="24" r="16" />
              <path d="M24 16v16" />
              <path d="M16 24l8 8 8-8" />
            </svg>
            <svg v-else viewBox="0 0 48 48" aria-hidden="true">
              <circle cx="24" cy="24" r="16" />
              <path d="M24 16v10l6 4" />
            </svg>
          </div>
          <div class="log-text">
            <p class="log-title">{{ selectedObservation.title }}</p>
            <p class="log-desc">{{ selectedObservation.detail }}</p>
          </div>
        </div>
        <div v-else class="log-empty">
          선택한 날에는 특이 사항이 관찰되지 않았습니다.
        </div>

        <div class="log-list">
          <button
            v-for="item in observationsWithIndex"
            :key="item.index"
            type="button"
            class="log-item"
            :class="{ active: item.index === selectedIndex }"
            @click="handlePointClick(item.index)"
          >
            <span class="log-badge" :class="item.type">{{ observationLabel(item.type) }}</span>
            <span class="log-date">{{ item.dateText }}</span>
            <span class="log-summary">{{ item.title }}</span>
          </button>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.history-container {
  display: flex;
  flex-direction: column;
  gap: 18px;
  height: 100%;
  overflow: hidden;
}

.loading {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e0e5ec;
  border-top-color: #4cb7b7;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.trend-card {
  background: #f5f6f7;
  padding: 20px 20px 16px;
  border-radius: 32px;
  box-shadow: 14px 14px 28px #cfd6df, -14px -14px 28px #ffffff;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.mint-dot {
  width: 12px;
  height: 12px;
  background: #4cb7b7;
  border-radius: 50%;
}

.section-header h3 {
  font-size: 22px;
  font-weight: 900;
  margin: 0;
}

.section-sub {
  margin: 4px 0 0;
  font-size: 18px;
  color: #666;
}

.legend {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 700;
  color: #555;
}

.legend-icon {
  width: 28px;
  height: 28px;
  border-radius: 10px;
  background: #ffffff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: inset 3px 3px 8px rgba(209, 217, 230, 0.6), inset -3px -3px 8px #ffffff;
}

.legend-icon svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: #4cb7b7;
  stroke-width: 2.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.legend-icon.pause svg {
  stroke: #ff8a80;
}

.legend-icon.hesitation svg {
  stroke: #ffb74d;
}

.insight-card {
  background: #ffffff;
  padding: 18px 20px;
  border-radius: 28px;
  box-shadow: 10px 10px 20px #d1d9e6, -10px -10px 20px #ffffff;
  display: grid;
  gap: 8px;
}

.insight-card h4 {
  font-size: 20px;
  font-weight: 900;
  margin: 0;
}

.insight-card p {
  margin: 0;
  font-size: 20px;
  color: #4d4d4d;
  line-height: 1.5;
}

.log-card {
  background: #f5f6f7;
  padding: 18px 20px;
  border-radius: 32px;
  box-shadow: 14px 14px 28px #cfd6df, -14px -14px 28px #ffffff;
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
  min-height: 0;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.log-header h4 {
  font-size: 22px;
  font-weight: 900;
  margin: 0;
}

.date-chip {
  padding: 8px 14px;
  border-radius: 18px;
  font-size: 18px;
  font-weight: 800;
  background: #ffffff;
  color: #4cb7b7;
  box-shadow: inset 4px 4px 10px rgba(209, 217, 230, 0.6), inset -4px -4px 10px #ffffff;
}

.log-detail {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 16px;
  align-items: center;
  padding: 16px;
  border-radius: 22px;
  background: #ffffff;
  box-shadow: inset 4px 4px 10px rgba(209, 217, 230, 0.6), inset -4px -4px 10px #ffffff;
}

.log-icon {
  width: 64px;
  height: 64px;
  border-radius: 18px;
  background: #f5f6f7;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: inset 4px 4px 10px rgba(209, 217, 230, 0.6), inset -4px -4px 10px #ffffff;
}

.log-icon svg {
  width: 36px;
  height: 36px;
  fill: none;
  stroke: #4cb7b7;
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.log-icon.pause svg {
  stroke: #ff8a80;
}

.log-icon.hesitation svg {
  stroke: #ffb74d;
}

.log-icon.task svg {
  stroke: #4cb7b7;
}

.log-icon.encouragement svg {
  stroke: #4cb7b7;
}

.log-text {
  display: grid;
  gap: 6px;
}

.log-title {
  margin: 0;
  font-size: 20px;
  font-weight: 900;
}

.log-desc {
  margin: 0;
  font-size: 18px;
  color: #555;
  line-height: 1.5;
}

.log-empty {
  padding: 16px;
  font-size: 18px;
  color: #777;
  background: #ffffff;
  border-radius: 22px;
  box-shadow: inset 4px 4px 10px rgba(209, 217, 230, 0.6), inset -4px -4px 10px #ffffff;
}

.log-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow: auto;
  padding-right: 4px;
}

.log-item {
  border: none;
  background: #ffffff;
  padding: 12px 14px;
  border-radius: 20px;
  display: grid;
  grid-template-columns: auto auto 1fr;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  cursor: pointer;
  box-shadow: 6px 6px 12px #d1d9e6, -6px -6px 12px #ffffff;
  text-align: left;
}

.log-item.active {
  outline: 2px solid rgba(76, 183, 183, 0.6);
}

.log-badge {
  padding: 6px 10px;
  border-radius: 12px;
  font-size: 18px;
  font-weight: 800;
  color: #4cb7b7;
  background: rgba(76, 183, 183, 0.15);
}

.log-badge.pause {
  color: #ff8a80;
  background: rgba(255, 138, 128, 0.15);
}

.log-badge.hesitation {
  color: #ffb74d;
  background: rgba(255, 183, 77, 0.2);
}

.log-badge.encouragement {
  color: #4cb7b7;
  background: rgba(76, 183, 183, 0.15);
}

.log-date {
  font-size: 18px;
  font-weight: 700;
  color: #777;
}

.log-summary {
  font-weight: 800;
  color: #2e2e2e;
}
</style>
