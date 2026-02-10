<script setup>
import { computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useCaregiverData } from '@/composables/useCaregiverData';
import WeeklyChart from '../WeeklyChart.vue';

const router = useRouter();
const { data, loading, fetchData } = useCaregiverData();

onMounted(() => {
  fetchData();
});

const dayNames = ['일', '월', '화', '수', '목', '금', '토'];
const lastSevenDays = computed(() => {
  const result = [];
  const today = new Date();
  for (let i = 6; i >= 0; i -= 1) {
    const d = new Date();
    d.setDate(today.getDate() - i);
    result.push(dayNames[d.getDay()]);
  }
  return result;
});

const observationIndices = computed(() => {
  const observations = data.value?.weeklyObservations ?? [];
  return observations
    .map((item) => 6 - item.dayOffset)
    .filter((index) => index >= 0 && index <= 6);
});

const statusTone = computed(() => {
  const label = data.value?.todayStatus?.label ?? '';
  if (label.includes('주의') || label.includes('관찰')) return 'alert';
  if (label.includes('위험') || label.includes('경고') || label.includes('심각')) return 'danger';
  return 'stable';
});

const statusColor = computed(() => {
  if (statusTone.value === 'danger') return '#ff8a80';
  if (statusTone.value === 'alert') return '#ffb74d';
  return '#4cb7b7';
});

const statusLabel = computed(() => data.value?.todayStatus?.label ?? '안정');
const subjectName = computed(() => data.value?.subject?.name ?? '대상자');
const relationText = computed(() => data.value?.subject?.relation ?? '가족');

const statusSummary = computed(() => `${subjectName.value} 님은 오늘 ${statusLabel.value} 상태입니다.`);
const statusMessage = computed(() => data.value?.todayStatus?.message ?? '오늘 대화 리듬이 안정적으로 유지되었습니다.');
const lastChatText = computed(() => data.value?.todayStatus?.lastChat ?? '오늘 기록 없음');

const trendSummary = computed(() => {
  const trend = data.value?.weeklyTrend?.trend ?? 'stable';
  if (trend === 'down') {
    return '최근 반응 속도의 변화가 있어 추가 관찰이 필요합니다.';
  }
  if (trend === 'up') {
    return '최근 반응 속도가 조금 더 부드럽게 유지되고 있습니다.';
  }
  return '최근 흐름이 안정적으로 유지되고 있습니다.';
});

const trendBadgeText = computed(() => {
  const trend = data.value?.weeklyTrend?.trend ?? 'stable';
  if (trend === 'down') return '관찰 필요';
  if (trend === 'up') return '안정 흐름';
  return '유지 중';
});

const emotionLabel = computed(() => {
  if (statusTone.value === 'danger') return '주의가 필요한 대화 톤';
  if (statusTone.value === 'alert') return '관찰이 필요한 대화 톤';
  return '안정적인 대화 톤';
});

const quickActions = computed(() => {
  if (!data.value) return [];
  return [
    {
      id: 'weekly',
      title: '주간 대화',
      value: `${data.value.weeklyActivity.completed}/${data.value.weeklyActivity.total}회`,
      desc: '이번 주 참여',
      icon: 'mic',
      tone: 'mint',
      action: 'history',
    },
    {
      id: 'recent',
      title: '최근 대화',
      value: lastChatText.value,
      desc: '기록 바로 보기',
      icon: 'doc',
      tone: 'neutral',
      action: 'history',
    },
  ];
});

const handleAction = (action) => {
  if (action === 'history') {
    router.push({ name: 'history' });
  }
};

const statusIconPath = computed(() => {
  if (statusTone.value === 'danger') {
    return 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 13h-2v-2h2v2zm0-4h-2V6h2v5z';
  }
  if (statusTone.value === 'alert') {
    return 'M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z';
  }
  return 'M9 16.2l-3.5-3.5L4 14.2l5 5 11-11-1.5-1.5L9 16.2z';
});
</script>

<template>
  <div class="caregiver-home-container">
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
    </div>

    <template v-else-if="data">
      <section class="hero-card stagger" style="--delay: 0ms">
        <div class="hero-header">
          <div>
            <p class="hero-caption">{{ relationText }} 보호자 대시보드</p>
            <h2 class="hero-title">{{ subjectName }} 님</h2>
          </div>
          <div class="status-pill" :class="statusTone">
            <span class="status-dot"></span>
            <span>{{ statusLabel }}</span>
          </div>
        </div>

        <div class="hero-body">
          <div class="status-visual" :class="statusTone">
            <svg viewBox="0 0 24 24" :style="{ color: statusColor }">
              <path :d="statusIconPath" fill="currentColor" />
            </svg>
          </div>
          <div class="hero-text">
            <p class="hero-message">{{ statusSummary }}</p>
            <p class="hero-detail">{{ statusMessage }}</p>
            <p class="hero-meta">마지막 대화 {{ lastChatText }}</p>
          </div>
        </div>

        <div class="hero-footer">
          <div class="emotion-chip">
            <svg viewBox="0 0 48 48" class="emotion-icon" aria-hidden="true">
              <circle cx="24" cy="24" r="18" />
              <path d="M16 26c2.5 3 13.5 3 16 0" />
              <circle cx="18" cy="20" r="2" />
              <circle cx="30" cy="20" r="2" />
            </svg>
            <span>{{ emotionLabel }}</span>
          </div>
          <div v-if="data.alerts.length" class="alert-chip">
            알림 {{ data.alerts.length }}건
          </div>
        </div>
      </section>

      <section class="trend-card stagger" style="--delay: 120ms">
        <div class="trend-header">
          <div>
            <h3>최근 7일 대화 흐름</h3>
            <p class="trend-message">{{ trendSummary }}</p>
          </div>
          <span class="trend-badge" :class="data.weeklyTrend.trend">
            {{ trendBadgeText }}
          </span>
        </div>
        <WeeklyChart
          :data="data.weeklyTrend.scores"
          :labels="lastSevenDays"
          :highlights="observationIndices"
        />
        <p class="trend-hint">표식된 날은 평소보다 발화 리듬 변화가 관찰된 날입니다.</p>
      </section>

      <section class="quick-actions">
        <button
          v-for="(item, index) in quickActions"
          :key="item.id"
          class="action-card stagger"
          :style="{ '--delay': `${240 + index * 120}ms` }"
          :disabled="!item.action"
          type="button"
          @click="handleAction(item.action)"
        >
          <div class="action-icon" :class="item.tone">
            <svg v-if="item.icon === 'mic'" viewBox="0 0 48 48" aria-hidden="true">
              <path d="M24 30a6 6 0 0 0 6-6V12a6 6 0 0 0-12 0v12a6 6 0 0 0 6 6z" />
              <path d="M34 22a10 10 0 0 1-20 0H10a14 14 0 0 0 12 13.8V40h4v-4.2A14 14 0 0 0 38 22h-4z" />
              <circle class="icon-pulse" cx="24" cy="24" r="18" />
            </svg>
            <svg v-else-if="item.icon === 'trend'" viewBox="0 0 48 48" aria-hidden="true">
              <path d="M8 30l10-10 8 8 14-14" />
              <circle class="icon-dot" cx="18" cy="20" r="3" />
              <circle class="icon-dot" cx="26" cy="28" r="3" />
              <circle class="icon-dot" cx="40" cy="14" r="3" />
            </svg>
            <svg v-else viewBox="0 0 48 48" aria-hidden="true">
              <rect x="12" y="10" width="24" height="28" rx="6" />
              <path d="M18 20h12M18 26h12M18 32h8" />
              <circle class="icon-search" cx="36" cy="36" r="6" />
              <path class="icon-search" d="M41 41l-4-4" />
            </svg>
          </div>
          <div class="action-text">
            <h4>{{ item.title }}</h4>
            <p>{{ item.value }}</p>
            <span>{{ item.desc }}</span>
          </div>
        </button>
      </section>
    </template>
  </div>
</template>

<style scoped>
.caregiver-home-container {
  --card-surface: #f7f9fa;
  --card-elevation-main:
    0 10px 22px rgba(126, 140, 154, 0.18),
    0 3px 8px rgba(126, 140, 154, 0.11),
    0 1px 3px rgba(126, 140, 154, 0.06);
  --card-elevation-sub:
    0 8px 16px rgba(126, 140, 154, 0.14),
    0 2px 6px rgba(126, 140, 154, 0.1);
  --card-elevation-icon:
    0 10px 18px rgba(126, 140, 154, 0.18),
    0 3px 8px rgba(126, 140, 154, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.62);
  --card-elevation-hover:
    0 11px 20px rgba(126, 140, 154, 0.16),
    0 4px 10px rgba(126, 140, 154, 0.12);
  display: flex;
  flex-direction: column;
  gap: 24px;
  min-height: 100%;
  overflow: visible;
  justify-content: flex-start;
  padding-bottom: 12px;
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

.hero-card {
  background: var(--card-surface);
  padding: 20px 20px 18px;
  border-radius: 24px;
  box-shadow: var(--card-elevation-main);
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.hero-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.hero-caption {
  font-size: 18px;
  font-weight: 700;
  color: #4cb7b7;
  margin: 0 0 6px;
}

.hero-title {
  font-size: 28px;
  font-weight: 900;
  color: #2e2e2e;
  margin: 0;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 999px;
  font-size: 18px;
  font-weight: 800;
  background: #e6f3f3;
  color: #1f5f5f;
  white-space: nowrap;
  box-shadow: inset 2px 2px 4px rgba(0, 0, 0, 0.08), inset -2px -2px 4px rgba(255, 255, 255, 0.9);
}

.status-pill.stable {
  background: rgba(76, 183, 183, 0.15);
  color: #1f5f5f;
}

.status-pill.alert {
  background: rgba(255, 183, 77, 0.2);
  color: #c77715;
}

.status-pill.danger {
  background: rgba(255, 138, 128, 0.18);
  color: #d66a61;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: currentColor;
}

.hero-body {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 16px;
  align-items: center;
}

.status-visual {
  width: 92px;
  height: 92px;
  border-radius: 24px;
  background: #f9fbfb;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--card-elevation-icon);
}

.status-visual svg {
  width: 44px;
  height: 44px;
}

.hero-message {
  font-size: 24px;
  font-weight: 900;
  margin: 0 0 6px;
  color: #2e2e2e;
}

.hero-detail {
  font-size: 20px;
  margin: 0 0 6px;
  color: #4d4d4d;
  line-height: 1.5;
}

.hero-meta {
  font-size: 18px;
  margin: 0;
  color: #8a8a8a;
}

.hero-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.emotion-chip {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 999px;
  background: #f8fafb;
  font-size: 18px;
  font-weight: 700;
  color: #2e2e2e;
  box-shadow: var(--card-elevation-sub);
}

.emotion-icon {
  width: 32px;
  height: 32px;
  fill: none;
  stroke: #4cb7b7;
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
  animation: emotionPulse 2.6s ease-in-out infinite;
}

.alert-chip {
  padding: 10px 14px;
  border-radius: 20px;
  font-size: 18px;
  font-weight: 800;
  color: #d66a61;
  background: rgba(255, 138, 128, 0.15);
}

.trend-card {
  background: var(--card-surface);
  padding: 20px 20px 16px;
  border-radius: 24px;
  box-shadow: var(--card-elevation-main);
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: none;
}

.trend-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.trend-header h3 {
  font-size: 22px;
  font-weight: 900;
  margin: 0 0 6px;
  color: #2e2e2e;
}

.trend-message {
  font-size: 20px;
  margin: 0;
  color: #4d4d4d;
  line-height: 1.5;
}

.trend-badge {
  padding: 8px 14px;
  border-radius: 18px;
  font-size: 20px;
  font-weight: 900;
  background: #e8f5f5;
  color: #4cb7b7;
  white-space: nowrap;
}

.trend-badge.down {
  background: rgba(255, 138, 128, 0.18);
  color: #ff8a80;
}

.trend-hint {
  font-size: 18px;
  color: #7a7a7a;
  margin: 6px 0 0;
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  align-items: stretch;
}

.action-card {
  border: none;
  background: var(--card-surface);
  padding: 16px 12px;
  border-radius: 24px;
  box-shadow: var(--card-elevation-sub);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  text-align: center;
  cursor: pointer;
  min-height: 150px;
  transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
  overflow: hidden;
  min-width: 0;
}

.action-card:disabled {
  cursor: default;
  opacity: 0.76;
}

.action-card:active:not(:disabled) {
  transform: translateY(1px) scale(0.995);
}

.action-card:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: var(--card-elevation-hover);
}

.action-icon {
  width: 64px;
  height: 64px;
  border-radius: 18px;
  background: #f9fbfb;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--card-elevation-icon);
}

.action-icon svg {
  width: 40px;
  height: 40px;
  fill: none;
  stroke: #4cb7b7;
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.action-icon.mint svg {
  stroke: #4cb7b7;
}

.action-icon.alert svg {
  stroke: #ff8a80;
}

.action-icon.neutral svg {
  stroke: #4d4d4d;
}

.action-text h4 {
  font-size: 20px;
  font-weight: 800;
  margin: 0;
  color: #2e2e2e;
}

.action-text p {
  font-size: 20px;
  font-weight: 900;
  margin: 4px 0 0;
  color: #4cb7b7;
}

.action-text span {
  font-size: 18px;
  color: #777;
}

.icon-pulse {
  fill: none;
  stroke: rgba(76, 183, 183, 0.35);
  stroke-width: 2;
  animation: iconPulse 2.6s ease-in-out infinite;
}

.icon-dot {
  fill: #4cb7b7;
  animation: dotBounce 2s ease-in-out infinite;
}

.icon-search {
  fill: none;
  stroke: #4cb7b7;
  stroke-width: 3;
  stroke-linecap: round;
}

.stagger {
  opacity: 0;
  transform: translateY(12px);
  animation: fadeUp 0.6s ease forwards;
  animation-delay: var(--delay, 0ms);
}

@keyframes fadeUp {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes emotionPulse {
  0%, 100% { transform: scale(1); opacity: 0.8; }
  50% { transform: scale(1.1); opacity: 1; }
}

@keyframes iconPulse {
  0%, 100% { transform: scale(0.9); opacity: 0.4; }
  50% { transform: scale(1.1); opacity: 0.9; }
}

@keyframes dotBounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}

@media (prefers-reduced-motion: reduce) {
  .stagger,
  .emotion-icon,
  .icon-pulse,
  .icon-dot {
    animation: none !important;
  }
}
</style>
