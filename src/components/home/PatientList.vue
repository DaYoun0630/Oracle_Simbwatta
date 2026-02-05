<script setup>
import { computed, ref, watch } from 'vue';

const props = defineProps({
  patients: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  pageSize: {
    type: Number,
    default: 20
  }
});

const emit = defineEmits(['select']);

const containerRef = ref(null);
const expandedId = ref(null);
const visibleCount = ref(props.pageSize);

const visiblePatients = computed(() => props.patients.slice(0, visibleCount.value));

const handleScroll = () => {
  if (!containerRef.value) return;
  const { scrollTop, scrollHeight, clientHeight } = containerRef.value;
  if (scrollHeight - scrollTop - clientHeight < 120) {
    visibleCount.value = Math.min(props.patients.length, visibleCount.value + props.pageSize);
  }
};

const toggleExpand = (patientId) => {
  expandedId.value = expandedId.value === patientId ? null : patientId;
};

const handleSelect = (patient) => {
  emit('select', patient);
};

const getRiskClass = (patient) => {
  const cdr = patient.cdrSB ?? null;
  if (cdr !== null) {
    if (cdr >= 2) return 'high';
    if (cdr > 0.5) return 'mid';
    return 'low';
  }
  if (patient.riskLevel === 'high') return 'high';
  if (patient.riskLevel === 'mid') return 'mid';
  return 'low';
};

const getSparklinePath = (scores) => {
  if (!scores || scores.length < 2) return '';
  const width = 120;
  const height = 40;
  const padding = 4;
  const min = Math.min(...scores);
  const max = Math.max(...scores);
  const range = max - min || 1;
  const points = scores.map((score, i) => {
    const x = padding + (i / (scores.length - 1)) * (width - padding * 2);
    const y = height - padding - ((score - min) / range) * (height - padding * 2);
    return `${x},${y}`;
  });
  return `M ${points.join(' L ')}`;
};

const formatPercent = (value) => (typeof value === 'number' ? `${value}%` : '-');

const formatViscode = (value) => (value ? value.toUpperCase() : '');

const getRecentVisit = (patient) => patient.lastVisit || patient.examDate || '-';

const isMmseWarning = (patient) => typeof patient.mmse === 'number' && patient.mmse <= 26;

watch(() => props.patients, () => {
  visibleCount.value = props.pageSize;
  expandedId.value = null;
  if (containerRef.value) {
    containerRef.value.scrollTop = 0;
  }
});

</script>

<template>
  <div class="registry-table">
    <div class="table-header">
      <div class="cell status"></div>
      <div class="cell id">ID</div>
      <div class="cell age">나이</div>
      <div class="cell score">MMSE</div>
      <div class="cell score">성취도</div>
      <div class="cell recent">최근 접속</div>
    </div>

    <div ref="containerRef" class="table-body" @scroll="handleScroll">
      <div v-if="loading" class="skeleton-row" v-for="index in 6" :key="index"></div>

      <template v-else>
        <div v-for="patient in visiblePatients" :key="patient.id" class="row-wrapper">
          <div class="table-row" :class="{ warning: isMmseWarning(patient) }" @click="toggleExpand(patient.id)">
            <div class="cell status">
              <span class="status-dot" :class="getRiskClass(patient)"></span>
            </div>
            <div class="cell id">
              <span class="id-main">{{ patient.id }}</span>
              <span class="id-sub">{{ patient.rid }}</span>
            </div>
            <div class="cell age">{{ patient.age }}세</div>
            <div class="cell score">{{ patient.mmse ?? '-' }}</div>
            <div class="cell score">{{ formatPercent(patient.participationRate) }}</div>
            <div class="cell recent">
              {{ getRecentVisit(patient) }}
              <span v-if="patient.latestViscode2" class="recent-viscode">({{ formatViscode(patient.latestViscode2) }})</span>
            </div>
          </div>

          <div v-if="expandedId === patient.id" class="row-detail">
            <div class="detail-main">
              <div>
                <strong>{{ patient.name }}</strong>
                <span>{{ patient.age }}세 · {{ patient.gender === 'F' ? '여' : '남' }}</span>
              </div>
              <button class="detail-btn" @click.stop="handleSelect(patient)">상세 보기</button>
            </div>
            <div class="detail-grid">
              <div class="detail-card">
                <span>진단</span>
                <strong>{{ patient.diagnosis }}</strong>
              </div>
              <div class="detail-card">
                <span>참여율</span>
                <strong>{{ patient.participationRate }}%</strong>
              </div>
              <div class="detail-card">
                <span>최근 방문</span>
                <strong>{{ patient.lastVisit }}</strong>
              </div>
            </div>
            <div class="sparkline-box">
              <span>7일 발화 안정성</span>
              <svg viewBox="0 0 120 40">
                <path :d="getSparklinePath(patient.weeklyScores)" stroke="#4cb7b7" fill="none" stroke-width="2" stroke-linecap="round" />
              </svg>
            </div>
          </div>
        </div>

        <div v-if="visiblePatients.length === 0" class="empty-state">
          조건에 해당하는 환자가 없습니다.
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.registry-table {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  min-height: 0;
}

.table-header {
  display: grid;
  grid-template-columns: 12px 1.6fr 0.6fr 0.6fr 0.8fr 1fr;
  gap: 8px;
  padding: 14px 16px;
  border-radius: 18px;
  background: #ffffff;
  box-shadow: inset 4px 4px 8px rgba(209, 217, 230, 0.6), inset -4px -4px 8px #ffffff;
  font-size: 16px;
  font-weight: 800;
  color: #777;
}

.table-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 20px;
  border-radius: 20px;
  background: #f5f6f7;
  max-height: clamp(260px, 42vh, 520px);
}

.row-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.table-row {
  display: grid;
  grid-template-columns: 12px 1.6fr 0.6fr 0.6fr 0.8fr 1fr;
  gap: 8px;
  align-items: center;
  background: #ffffff;
  padding: 14px 16px;
  border-radius: 16px;
  box-shadow: 6px 6px 12px rgba(209, 217, 230, 0.6), -6px -6px 12px #ffffff;
  cursor: pointer;
}

.table-row.warning {
  background: linear-gradient(135deg, rgba(255, 183, 77, 0.18), rgba(255, 224, 178, 0.28));
}

.cell {
  font-size: 16px;
  font-weight: 700;
  color: #2e2e2e;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cell.id {
  display: flex;
  flex-direction: column;
  gap: 4px;
  white-space: normal;
}

.id-main {
  font-size: 16px;
  font-weight: 800;
  color: #4cb7b7;
}

.id-sub {
  font-size: 16px;
  font-weight: 700;
  color: #777;
}

.cell.score,
.cell.age,
.cell.recent {
  text-align: right;
  font-weight: 800;
}

.cell.recent {
  white-space: normal;
  line-height: 1.2;
}

.recent-viscode {
  color: #4cb7b7;
  font-weight: 800;
}

.cell.status {
  display: flex;
  justify-content: center;
}

.status-dot {
  width: 10px;
  height: 36px;
  border-radius: 999px;
  background: #4cb7b7;
}

.status-dot.mid {
  background: #ffb74d;
}

.status-dot.high {
  background: #ff8a80;
}

.row-detail {
  background: #f5f6f7;
  border-radius: 18px;
  padding: 16px;
  box-shadow: inset 4px 4px 8px rgba(209, 217, 230, 0.6), inset -4px -4px 8px #ffffff;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.detail-main strong {
  font-size: 18px;
  font-weight: 800;
  color: #2e2e2e;
  display: block;
}

.detail-main span {
  font-size: 16px;
  font-weight: 700;
  color: #777;
}

.detail-btn {
  border: none;
  border-radius: 16px;
  padding: 10px 16px;
  background: #4cb7b7;
  color: #ffffff;
  font-size: 16px;
  font-weight: 800;
  cursor: pointer;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.detail-card {
  background: #ffffff;
  border-radius: 14px;
  padding: 12px;
  box-shadow: inset 4px 4px 8px rgba(209, 217, 230, 0.5), inset -4px -4px 8px #ffffff;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.detail-card span {
  font-size: 16px;
  font-weight: 700;
  color: #888;
}

.detail-card strong {
  font-size: 16px;
  font-weight: 800;
}

.sparkline-box {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 16px;
  font-weight: 700;
  color: #555;
}

.sparkline-box svg {
  width: 100%;
  height: 40px;
}

.skeleton-row {
  height: 56px;
  border-radius: 16px;
  background: linear-gradient(90deg, #e0e5ec 25%, #f0f3f6 50%, #e0e5ec 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  margin-bottom: 12px;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.empty-state {
  padding: 40px 16px;
  text-align: center;
  font-size: 16px;
  font-weight: 700;
  color: #888;
}

@media (max-width: 520px) {
  .table-header,
  .table-row {
    grid-template-columns: 10px 1.4fr 0.6fr 0.6fr 0.8fr 0.9fr;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
