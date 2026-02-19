<script setup>
import { computed } from 'vue';
import { useRouter } from 'vue-router';

const props = defineProps({
  doctorData: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  },
  currentTab: {
    type: String,
    default: 'summary'
  },
  openPatientSheet: {
    type: Function,
    default: null
  },
  isPatientSheetOpen: {
    type: Boolean,
    default: false
  }
});

const router = useRouter();

const currentPatient = computed(() => props.doctorData?.currentPatient || null);
const patientRecord = computed(() => {
  if (!props.doctorData?.patients?.length || !currentPatient.value) return null;
  return props.doctorData.patients.find((patient) => patient.id === currentPatient.value.id) || props.doctorData.patients[0];
});

const visits = computed(() => props.doctorData?.visits || []);
const sortedVisits = computed(() => {
  if (!visits.value.length) return [];
  return [...visits.value].sort((a, b) => new Date(a.examDate).getTime() - new Date(b.examDate).getTime());
});
const latestVisit = computed(() => sortedVisits.value.at(-1) || null);
const previousVisit = computed(() => (sortedVisits.value.length > 1 ? sortedVisits.value.at(-2) : null));

const clinicalAssessment = computed(() => props.doctorData?.clinicalAssessment || null);

const mmseScore = computed(() =>
  clinicalAssessment.value?.mmse?.score
  ?? latestVisit.value?.mmse
  ?? patientRecord.value?.mmse
  ?? null
);

const mocaScore = computed(() =>
  clinicalAssessment.value?.moca?.score
  ?? latestVisit.value?.moca
  ?? patientRecord.value?.moca
  ?? null
);

const cdrScore = computed(() =>
  clinicalAssessment.value?.cdrSB?.score
  ?? latestVisit.value?.cdrSB
  ?? patientRecord.value?.cdrSB
  ?? null
);

const lastUpdated = computed(() =>
  latestVisit.value?.examDate
  ?? patientRecord.value?.lastVisit
  ?? '-'
);

const genderLabel = computed(() => (patientRecord.value?.gender === 'F' ? '여' : '남'));

// 환자 목록 버튼을 노출할 수 있는지 판단한다
const canOpenPatientSheet = computed(() => typeof props.openPatientSheet === 'function');

const riskLevel = computed(() => {
  const score = typeof cdrScore.value === 'number' ? cdrScore.value : 0;
  if (score >= 2) return 'high';
  if (score > 0.5) return 'mid';
  return 'low';
});

const riskLabel = computed(() => {
  if (riskLevel.value === 'high') return 'HIGH';
  if (riskLevel.value === 'mid') return 'MID';
  return 'LOW';
});

const mmseDelta = computed(() => {
  if (!latestVisit.value || !previousVisit.value) return null;
  if (typeof latestVisit.value.mmse !== 'number' || typeof previousVisit.value.mmse !== 'number') return null;
  return latestVisit.value.mmse - previousVisit.value.mmse;
});

const mocaDelta = computed(() => {
  if (!latestVisit.value || !previousVisit.value) return null;
  if (typeof latestVisit.value.moca !== 'number' || typeof previousVisit.value.moca !== 'number') return null;
  return latestVisit.value.moca - previousVisit.value.moca;
});

const formatDelta = (value) => {
  if (value === null || Number.isNaN(value)) return '최근 변화 없음';
  if (value === 0) return '변화 없음';
  return value > 0 ? `▲ ${value}` : `▼ ${Math.abs(value)}`;
};

const formatScore = (value) => (typeof value === 'number' ? value : '-');

const goToReport = () => {
  if (!currentPatient.value?.id) return;
  router.push({ name: 'doctor-report', params: { patientId: currentPatient.value.id } });
};
</script>

<template>
  <div class="doctor-home summary-hub">
    <div v-if="loading || !doctorData" class="loading">
      <div class="skeleton-card"></div>
      <div class="skeleton-row"></div>
      <div class="skeleton-card"></div>
    </div>

    <template v-else>
      <section class="patient-card">
        <div class="patient-main">
          <h2>{{ currentPatient?.name }}</h2>
          <p class="patient-id">{{ currentPatient?.id }}</p>
          <p class="patient-sub">
            {{ patientRecord?.age }}세 · {{ genderLabel }} · 최근 검사 {{ lastUpdated }}
          </p>
        </div>
        <span class="risk-badge" :class="riskLevel">{{ riskLabel }}</span>
      </section>

      <button
        v-if="canOpenPatientSheet"
        type="button"
        class="patient-list-trigger"
        aria-haspopup="dialog"
        :aria-expanded="isPatientSheetOpen"
        aria-controls="patient-sheet"
        @click="openPatientSheet"
      >
        <span class="patient-list-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="22" height="22">
            <path
              d="M7 4a2 2 0 1 1 0 4a2 2 0 0 1 0-4zm10 0a2 2 0 1 1 0 4a2 2 0 0 1 0-4zM4 10h6a3 3 0 0 1 3 3v5H4v-5a3 3 0 0 1 3-3zm10 0h6a3 3 0 0 1 3 3v5h-6v-5a3 3 0 0 1 3-3z"
              fill="currentColor"
            />
          </svg>
        </span>
        <span class="patient-list-text">
          <span class="patient-list-title">환자 목록</span>
          <span class="patient-list-sub">
            현재 선택: {{ currentPatient?.name || '-' }} · {{ currentPatient?.id || '-' }}
          </span>
        </span>
        <span class="patient-list-chev" :class="{ open: isPatientSheetOpen }" aria-hidden="true">▾</span>
      </button>

      <section class="score-grid">
        <div class="score-card">
          <span class="score-label">MMSE</span>
          <strong class="score-value">{{ formatScore(mmseScore) }}</strong>
          <span class="score-delta">{{ formatDelta(mmseDelta) }}</span>
        </div>
        <div class="score-card">
          <span class="score-label">MoCA</span>
          <strong class="score-value">{{ formatScore(mocaScore) }}</strong>
          <span class="score-delta">{{ formatDelta(mocaDelta) }}</span>
        </div>
      </section>

      <section class="risk-card">
        <span class="risk-label">CDR-SB</span>
        <strong class="risk-score">{{ formatScore(cdrScore) }}</strong>
        <p class="risk-sub">종합 위험도 {{ riskLabel }}</p>
      </section>

      <button class="detail-button" type="button" @click="goToReport">
        환자 리포트 보기
      </button>
    </template>
  </div>
</template>

<style>
.doctor-home {
  display: flex;
  flex-direction: column;
  gap: 24px;
  font-size: 18px;
  min-height: 0;
}

.doctor-home .loading {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.doctor-home .skeleton-card {
  height: 160px;
  border-radius: 24px;
  background: linear-gradient(90deg, #e0e5ec 25%, #f0f3f6 50%, #e0e5ec 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

.doctor-home .skeleton-row {
  height: 100px;
  border-radius: 20px;
  background: linear-gradient(90deg, #e0e5ec 25%, #f0f3f6 50%, #e0e5ec 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.doctor-home .patient-card {
  background: #f5f6f7;
  padding: 24px;
  border-radius: 26px;
  box-shadow: 12px 12px 24px #d1d9e6, -12px -12px 24px #ffffff;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.doctor-home .patient-main h2 {
  font-size: 24px;
  font-weight: 800;
  margin: 0 0 6px;
  color: #2e2e2e;
}

.doctor-home .patient-id {
  margin: 0 0 6px;
  font-weight: 700;
  color: #4cb7b7;
}

.doctor-home .patient-sub {
  margin: 0;
  font-weight: 700;
  color: #777;
}

.doctor-home .risk-badge {
  min-width: 90px;
  text-align: center;
  padding: 10px 16px;
  border-radius: 999px;
  font-size: 18px;
  font-weight: 800;
  text-transform: uppercase;
}

.doctor-home .risk-badge.low {
  background: rgba(76, 183, 183, 0.15);
  color: #4cb7b7;
}

.doctor-home .risk-badge.mid {
  background: rgba(255, 183, 77, 0.2);
  color: #f5a623;
}

.doctor-home .risk-badge.high {
  background: rgba(255, 138, 128, 0.2);
  color: #ff8a80;
}

.doctor-home .patient-list-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border: none;
  border-radius: 22px;
  padding: 18px 20px;
  background: #f5f6f7;
  box-shadow: 12px 12px 24px #d1d9e6, -12px -12px 24px #ffffff;
  cursor: pointer;
  text-align: left;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.doctor-home .patient-list-trigger:hover {
  transform: translateY(-1px);
  box-shadow: 14px 14px 26px #cfd6df, -14px -14px 26px #ffffff;
}

.doctor-home .patient-list-trigger:active {
  transform: translateY(0);
  box-shadow: inset 6px 6px 12px rgba(209, 217, 230, 0.7), inset -6px -6px 12px #ffffff;
}

.doctor-home .patient-list-icon {
  width: 46px;
  height: 46px;
  border-radius: 16px;
  background: #ffffff;
  color: #4cb7b7;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: inset 4px 4px 10px rgba(209, 217, 230, 0.6), inset -4px -4px 10px #ffffff;
  flex-shrink: 0;
}

.doctor-home .patient-list-text {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.doctor-home .patient-list-title {
  font-size: 20px;
  font-weight: 900;
  color: #2e2e2e;
}

.doctor-home .patient-list-sub {
  font-size: 16px;
  font-weight: 700;
  color: #5f5f5f;
}

.doctor-home .patient-list-chev {
  font-size: 18px;
  font-weight: 900;
  color: #4cb7b7;
  transition: transform 0.2s ease;
}

.doctor-home .patient-list-chev.open {
  transform: rotate(180deg);
}

.doctor-home .score-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.doctor-home .score-card {
  background: #ffffff;
  padding: 24px;
  border-radius: 24px;
  box-shadow: inset 6px 6px 12px rgba(209, 217, 230, 0.6), inset -6px -6px 12px #ffffff;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}

.doctor-home .score-label {
  font-size: 18px;
  font-weight: 800;
  color: #777;
}

.doctor-home .score-value {
  font-size: 40px;
  font-weight: 900;
  color: #2e2e2e;
  line-height: 1;
}

.doctor-home .score-delta {
  font-size: 18px;
  font-weight: 700;
  color: #4cb7b7;
}

.doctor-home .risk-card {
  background: #f5f6f7;
  padding: 24px;
  border-radius: 24px;
  box-shadow: 12px 12px 24px #d1d9e6, -12px -12px 24px #ffffff;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.doctor-home .risk-label {
  font-size: 18px;
  font-weight: 800;
  color: #777;
}

.doctor-home .risk-score {
  font-size: 38px;
  font-weight: 900;
  color: #2e2e2e;
}

.doctor-home .risk-sub {
  margin: 0;
  font-weight: 700;
  color: #555;
}

.doctor-home .detail-button {
  border: none;
  border-radius: 20px;
  padding: 16px 20px;
  font-size: 18px;
  font-weight: 800;
  background: #4cb7b7;
  color: #ffffff;
  cursor: pointer;
  box-shadow: 6px 6px 12px rgba(76, 183, 183, 0.3);
}

@media (max-width: 520px) {
  .doctor-home .score-grid {
    grid-template-columns: 1fr;
  }

  .doctor-home .patient-card {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
