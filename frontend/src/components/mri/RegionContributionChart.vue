<script setup lang="ts">
import { computed } from 'vue';

interface RegionContribution {
  region: string;
  percentage: number;
  severity: 'high' | 'medium' | 'low';
}

const props = defineProps<{
  contributions: RegionContribution[];
  loading?: boolean;
}>();

const hasData = computed(() => props.contributions && props.contributions.length > 0);

const getSeverityColor = (severity: string) => {
  switch (severity) {
    case 'high':
      return '#EF4444'; // red
    case 'medium':
      return '#F97316'; // orange
    case 'low':
      return '#EAB308'; // yellow
    default:
      return '#9CA3AF'; // gray
  }
};

const getSeverityLabel = (severity: string) => {
  switch (severity) {
    case 'high':
      return '높음';
    case 'medium':
      return '중간';
    case 'low':
      return '낮음';
    default:
      return '-';
  }
};
</script>

<template>
  <div class="region-chart-container">
    <div class="chart-header">
      <h4>부위별 MCI 기여도 분석</h4>
      <p class="chart-description">AI 모델이 분석한 각 뇌 부위의 MCI 위험 기여도입니다.</p>
    </div>

    <!-- 로딩 상태 -->
    <div v-if="loading" class="loading-state">
      <div class="skeleton-bar" v-for="i in 4" :key="i"></div>
    </div>

    <!-- 데이터 없음 -->
    <div v-else-if="!hasData" class="empty-state">
      <span>분석 결과가 없습니다</span>
    </div>

    <!-- 기여도 막대 차트 -->
    <div v-else class="contribution-list">
      <div
        v-for="(item, index) in contributions"
        :key="index"
        class="contribution-item"
      >
        <div class="contribution-header">
          <div class="region-info">
            <span class="region-name">{{ item.region }}</span>
            <span
              class="severity-badge"
              :style="{ backgroundColor: getSeverityColor(item.severity) + '20', color: getSeverityColor(item.severity) }"
            >
              {{ getSeverityLabel(item.severity) }}
            </span>
          </div>
          <span
            class="percentage-value"
            :style="{ color: getSeverityColor(item.severity) }"
          >
            {{ item.percentage.toFixed(1) }}%
          </span>
        </div>
        <div class="progress-bar-bg">
          <div
            class="progress-bar-fill"
            :style="{
              width: `${Math.min(item.percentage, 100)}%`,
              backgroundColor: getSeverityColor(item.severity)
            }"
          ></div>
        </div>
      </div>
    </div>

    <!-- 안내 메시지 -->
    <div v-if="hasData && !loading" class="info-box">
      <div class="info-icon">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="16" x2="12" y2="12"/>
          <line x1="12" y1="8" x2="12.01" y2="8"/>
        </svg>
      </div>
      <p>
        <strong>안내:</strong> 위 분석 결과는 AI 모델의 예측입니다.
        최종 진단은 의사의 확정이 필요합니다.
      </p>
    </div>
  </div>
</template>

<style scoped>
.region-chart-container {
  background: #ffffff;
  border-radius: 20px;
  padding: 20px;
  box-shadow: inset 4px 4px 10px rgba(209, 217, 230, 0.6), inset -4px -4px 10px #ffffff;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.chart-header h4 {
  font-size: 18px;
  font-weight: 800;
  color: #2e2e2e;
  margin: 0 0 8px;
}

.chart-description {
  font-size: 14px;
  font-weight: 600;
  color: #777;
  margin: 0;
  line-height: 1.5;
}

/* 로딩 스켈레톤 */
.loading-state {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.skeleton-bar {
  height: 48px;
  border-radius: 12px;
  background: linear-gradient(90deg, #e0e5ec 25%, #f0f3f6 50%, #e0e5ec 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* 데이터 없음 */
.empty-state {
  padding: 40px;
  text-align: center;
  color: #888;
  font-weight: 700;
  background: #f5f6f7;
  border-radius: 16px;
}

/* 기여도 리스트 */
.contribution-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.contribution-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.contribution-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.region-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.region-name {
  font-size: 16px;
  font-weight: 800;
  color: #2e2e2e;
}

.severity-badge {
  font-size: 11px;
  font-weight: 800;
  padding: 4px 8px;
  border-radius: 999px;
  letter-spacing: 0.3px;
}

.percentage-value {
  font-size: 20px;
  font-weight: 900;
}

/* 막대 차트 */
.progress-bar-bg {
  width: 100%;
  height: 12px;
  background: #e5e7eb;
  border-radius: 999px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.5s ease-out;
}

/* 안내 박스 */
.info-box {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  background: rgba(76, 183, 183, 0.08);
  border: 1px solid rgba(76, 183, 183, 0.3);
  border-radius: 14px;
}

.info-icon {
  flex-shrink: 0;
  color: #4cb7b7;
}

.info-box p {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #2e7d7d;
  line-height: 1.5;
}

.info-box strong {
  font-weight: 800;
}
</style>
