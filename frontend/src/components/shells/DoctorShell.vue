<script setup>
import { ref, computed, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import AppHeader from '@/components/AppHeader.vue';
import { useDoctorPatientStore } from '@/stores/doctorPatient';

const props = defineProps({
  title: {
    type: String,
    default: '환자 모니터링'
  },
  patients: {
    type: Array,
    default: () => []
  },
  currentPatientId: {
    type: String,
    default: 'p001'
  }
});

const emit = defineEmits(['patient-change', 'tab-change']);

const router = useRouter();
const route = useRoute();
const doctorPatientStore = useDoctorPatientStore();

const getRoutePatientId = () => {
  const rawParam = route.params?.patientId;
  const paramValue = Array.isArray(rawParam) ? rawParam[0] : rawParam;
  const rawQuery = route.query?.patientId;
  const queryValue = Array.isArray(rawQuery) ? rawQuery[0] : rawQuery;
  return paramValue || queryValue || null;
};

const selectedPatient = ref(getRoutePatientId() || props.currentPatientId);

// 환자 상세 화면에서 사용할 분석 탭을 정의한다
const topTabs = [
  { name: 'clinical', label: '인지 검사' },
  { name: 'voice', label: '음성·대화' },
  { name: 'mri', label: 'MRI 분석' }
];

// 의료진 전용 하단 네비게이션 구조를 정의한다
const bottomTabs = [
  {
    name: 'doctor-patients',
    label: '환자 현황',
    icon: 'M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z'
  },
  {
    name: 'doctor-report',
    label: '환자 리포트',
    icon: 'M3 5h2v2H3V5zm4 0h14v2H7V5zM3 11h2v2H3v-2zm4 0h14v2H7v-2zm-4 6h2v2H3v-2zm4 0h14v2H7v-2z'
  },
  {
    name: 'doctor-settings',
    label: '설정',
    icon: 'M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z'
  }
];

const currentTopTab = ref('clinical');

// 현재 라우트 기준으로 활성 네비게이션을 계산한다
const currentBottomTab = computed(() => {
  const name = route.name;
  if (name === 'doctor-patients') return 'doctor-patients';
  if (name === 'doctor-patient') return 'doctor-patients';
  if (name === 'doctor-report' || name === 'history') return 'doctor-report';
  if (name === 'doctor-settings') return 'doctor-settings';
  return 'doctor-patients';
});


const fontScale = ref(localStorage.getItem('ui-font-scale') || 'medium');

// 환자 리포트 페이지에서만 상단 분석 탭을 노출한다
const showTopTabs = computed(() => route.name === 'doctor-report' || route.name === 'history');

const riskLabelMap = {
  low: 'LOW',
  mid: 'MID',
  high: 'HIGH'
};

const formatGender = (gender) => {
  if (gender === 'F') return '여';
  if (gender === 'M') return '남';
  return '-';
};

const formatRiskLabel = (riskLevel) => riskLabelMap[riskLevel] || 'UNKNOWN';

const fontScaleMap = {
  small: '16px',
  medium: '18px',
  large: '20px'
};

const emptyPatient = {
  name: '환자 없음',
  id: '-',
  rid: '-',
  age: '-',
  gender: '-',
  hospital: '-'
};

const currentPatientInfo = computed(() => {
  const found = props.patients.find((patient) => patient.id === selectedPatient.value);
  return found || props.patients[0] || emptyPatient;
});

const patientLabel = computed(() => {
  const summary = doctorPatientStore.selectedPatientSummary;
  const info = summary?.id ? summary : currentPatientInfo.value;
  if (!info || info.id === '-' || info.name === '환자 없음') return '';
  return `${info.name} · ${info.id}`;
});

const switchTopTab = (tabName) => {
  currentTopTab.value = tabName;
  emit('tab-change', tabName);
};

const navigateTo = (tabName) => {
  if (tabName === 'doctor-report') {
    const patientId = selectedPatient.value || props.currentPatientId;
    if (patientId && patientId !== '-') {
      router.push({ name: 'doctor-report', params: { patientId } });
      return;
    }
    router.push({ name: 'doctor-patients' });
    return;
  }
  if (tabName === 'doctor-patients') {
    router.push({ name: 'doctor-patients' });
    return;
  }
  if (tabName === 'doctor-settings') {
    router.push({ name: 'doctor-settings' });
  }
};


watch(
  fontScale,
  (value) => {
    document.documentElement.style.fontSize = fontScaleMap[value] || '16px';
    localStorage.setItem('ui-font-scale', value);
  },
  { immediate: true }
);

watch(
  () => props.currentPatientId,
  (newId) => {
    selectedPatient.value = newId;
  }
);

watch(
  () => selectedPatient.value,
  (value) => {
    if (!value || value === '-') return;
    doctorPatientStore.setSelectedPatientId(value);
  },
  { immediate: true }
);

/* 환자 선택 시트 관련 상태 */
const patientSheetOpen = ref(false);

/* 환자 검색어 */
const patientQuery = ref('');
const normalizeSearchKeyword = (value) => String(value ?? '')
  .toLowerCase()
  .normalize('NFC')
  .replace(/\s+/g, '')
  .trim();

/* 환자 목록을 필터링 */
const filteredPatients = computed(() => {
  const q = normalizeSearchKeyword(patientQuery.value);
  if (!q) return props.patients;

  return props.patients.filter((p) => {
    const name = normalizeSearchKeyword(p?.name);
    const id = normalizeSearchKeyword(p?.id);
    const rid = normalizeSearchKeyword(p?.rid);
    return name.includes(q) || id.includes(q) || rid.includes(q);
  });
});

/* 헤더의 환자 표시 줄을 눌렀을 때 시트 열기 */
const openPatientSheet = () => {
  patientSheetOpen.value = true;
  patientQuery.value = '';
};

/* 시트 닫기 */
const closePatientSheet = () => {
  patientSheetOpen.value = false;
  patientQuery.value = '';
};

const updateRoutePatient = (patientId) => {
  if (!route.name) return;
  if (route.name === 'doctor-patient' || route.name === 'doctor-report') {
    router.replace({ name: route.name, params: { ...route.params, patientId }, query: route.query });
    return;
  }
  const nextQuery = { ...route.query, patientId };
  router.replace({ name: route.name, params: route.params, query: nextQuery });
};

/* 시트에서 환자 선택 */
const pickPatient = (patientId) => {
  if (!patientId || patientId === selectedPatient.value) {
    closePatientSheet();
    return;
  }
  selectedPatient.value = patientId;
  emit('patient-change', patientId);
  updateRoutePatient(patientId);
  closePatientSheet();
};

watch(
  () => getRoutePatientId(),
  (value) => {
    if (!value || value === selectedPatient.value) return;
    selectedPatient.value = value;
    emit('patient-change', value);
  }
);

watch(
  () => currentPatientInfo.value,
  (info) => {
    if (!info || info.id === '-' || info.name === '환자 없음') return;
    doctorPatientStore.setSelectedPatient({
      id: info.id,
      rid: info.rid,
      name: info.name,
      age: info.age,
      gender: info.gender,
      hospital: info.hospital
    });
  },
  { immediate: true }
);
</script>

<template>
  <div class="doctor-shell">
    <AppHeader
      :title="title"
      :showBackButton="true"
      :showMenuButton="false"
      :patientLabel="patientLabel"
      @back="router.back()"
    />

    <main class="content">
      <div v-if="showTopTabs" class="tabs-wrapper">
        <nav class="top-tabs">
          <button
            v-for="tab in topTabs"
            :key="tab.name"
            :class="['tab', { active: currentTopTab === tab.name }]"
            @click="switchTopTab(tab.name)"
          >
            {{ tab.label }}
          </button>
        </nav>
      </div>

      <!-- 기존 대시보드/히스토리 화면은 slot으로 유지 -->
      <slot
        :currentTab="currentTopTab"
        :openPatientSheet="openPatientSheet"
        :isPatientSheetOpen="patientSheetOpen"
      />
    </main>

    <nav class="bottom-nav">
      <button
        v-for="tab in bottomTabs"
        :key="tab.name"
        :class="['nav-item', { active: currentBottomTab === tab.name }]"
        @click="navigateTo(tab.name)"
      >
        <svg width="24" height="24" viewBox="0 0 24 24" class="icon">
          <path :d="tab.icon" :fill="currentBottomTab === tab.name ? '#4cb7b7' : '#999'" />
        </svg>
        <span class="label">{{ tab.label }}</span>
      </button>
    </nav>

    <!-- 환자 선택 시트 추가 -->
    <teleport to="body">
      <transition name="sheet-fade">
        <div
          v-if="patientSheetOpen"
          class="patient-sheet-backdrop"
          role="dialog"
          aria-modal="true"
          aria-label="환자 선택"
          @click.self="closePatientSheet"
        >
          <transition name="sheet-up">
            <section id="patient-sheet" class="patient-sheet" @click.stop>
              <header class="patient-sheet__header">
                <h2 class="patient-sheet__title">환자 목록</h2>
                <button type="button" class="patient-sheet__close" @click="closePatientSheet">
                  닫기
                </button>
              </header>

              <div class="patient-sheet__search">
                <input
                  v-model="patientQuery"
                  class="patient-sheet__input"
                  type="search"
                  placeholder="이름 / ID 검색"
                  autocomplete="off"
                />
              </div>

              <div class="patient-sheet__list" role="list">
                <button
                  v-for="p in filteredPatients"
                  :key="p.id"
                  type="button"
                  class="patient-row"
                  role="listitem"
                  :class="{ active: p.id === selectedPatient }"
                  @click="pickPatient(p.id)"
                >
                  <div class="patient-row__left">
                  <div class="patient-row__name">
                    <strong>{{ p.name }}</strong>
                    <span class="patient-row__meta">{{ p.age }}세 · {{ formatGender(p.gender) }}</span>
                  </div>
                  <div class="patient-row__sub">
                    <span class="muted">{{ p.id }}</span>
                    <span class="divider">·</span>
                    <span class="muted">{{ p.hospital || '-' }}</span>
                  </div>
                </div>
                <div class="patient-row__right">
                  <span class="risk-pill" :class="`risk-${p.riskLevel || 'unknown'}`">
                    {{ formatRiskLabel(p.riskLevel) }}
                  </span>
                </div>
              </button>

                <div v-if="filteredPatients.length === 0" class="patient-empty">
                  검색 결과가 없습니다.
                </div>
              </div>

              <footer class="patient-sheet__footer">
                <div class="patient-sheet__hint">
                  선택됨:
                  <strong>{{ currentPatientInfo?.name || '-' }}</strong>
                </div>
              </footer>
            </section>
          </transition>
        </div>
      </transition>
    </teleport>
  </div>
</template>

<style scoped>
.doctor-shell {
  min-height: 100vh;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f6f7;
}

.tabs-wrapper {
  display: flex;
  justify-content: center;
  padding: 0 0 12px;
  z-index: 1100;
}

.top-tabs {
  display: flex;
  gap: 10px;
  padding: 0;
  overflow-x: auto;
  flex-shrink: 0;
  scrollbar-width: none;
  width: 100%;
  max-width: 960px;
  justify-content: flex-start;
}

.top-tabs::-webkit-scrollbar {
  display: none;
}

.tab {
  padding: 12px 20px;
  border-radius: 18px;
  border: none;
  background: #fff;
  font-size: 18px;
  font-weight: 700;
  color: #888;
  cursor: pointer;
  white-space: nowrap;
  box-shadow: 2px 2px 4px #d1d9e6, -2px -2px 4px #ffffff;
  transition: all 0.2s;
}

.tab.active {
  background: #4cb7b7;
  color: #fff;
  box-shadow: 0 4px 8px rgba(76, 183, 183, 0.3);
}

.content {
  flex: 1;
  padding: 16px 20px 120px;
  overflow-y: auto;
  min-height: 0;
  max-width: 960px;
  margin: 0 auto;
  width: 100%;
}

.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 80px;
  background: #f5f6f7;
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding: 10px 20px 14px;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
  max-width: 960px;
  margin: 0 auto;
  z-index: 1100;
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  background: none;
  border: none;
  padding: 8px 12px;
  cursor: pointer;
  border-radius: 12px;
  transition: all 0.2s;
}

.nav-item.active {
  background: #fff;
  box-shadow: 2px 2px 6px #d1d9e6, -2px -2px 6px #ffffff;
}

.label {
  font-size: 18px;
  font-weight: 700;
  color: #999;
}

.nav-item.active .label {
  color: #4cb7b7;
}

/* 환자 선택 시트 */
.patient-sheet-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(20, 24, 28, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 18px;
  z-index: 1400;
}

.patient-sheet {
  width: min(520px, 100%);
  max-height: min(78vh, 720px);
  border-radius: 26px;
  background: #f5f6f7;
  box-shadow: 16px 16px 34px rgba(0, 0, 0, 0.18);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.patient-sheet__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 16px 10px;
}

.patient-sheet__title {
  margin: 0;
  font-size: 18px;
  font-weight: 900;
  color: #2e2e2e;
}

.patient-sheet__close {
  border: none;
  background: transparent;
  color: #4cb7b7;
  font-weight: 900;
  font-size: 14px;
  cursor: pointer;
}

.patient-sheet__search {
  padding: 0 16px 12px;
}

.patient-sheet__input {
  width: 100%;
  height: 48px;
  border: none;
  border-radius: 999px;
  padding: 0 16px;
  background: #eef1f3;
  box-shadow: inset 4px 4px 10px rgba(209, 217, 230, 0.9), inset -4px -4px 10px #ffffff;
  font-weight: 800;
  color: #2e2e2e;
}

.patient-sheet__input:focus {
  outline: none;
}

.patient-sheet__list {
  padding: 8px 10px 10px;
  overflow: auto;
  flex: 1;
  min-height: 0;
}

.patient-row {
  width: 100%;
  border: none;
  cursor: pointer;
  text-align: left;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 12px;
  border-radius: 18px;
  background: #ffffff;
  box-shadow: 10px 10px 18px #d1d9e6, -10px -10px 18px #ffffff;
  margin-bottom: 10px;
}

.patient-row.active {
  box-shadow: inset 6px 6px 14px rgba(209, 217, 230, 0.75), inset -6px -6px 14px #ffffff;
  background: #f7fbfb;
}

.patient-row__name {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 4px;
}

.patient-row__name strong {
  font-weight: 900;
  color: #2e2e2e;
}

.patient-row__meta {
  font-size: 13px;
  font-weight: 800;
  color: #777;
}

.patient-row__sub {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 12px;
}

.patient-row__right {
  display: flex;
  align-items: center;
}

.risk-pill {
  min-width: 64px;
  text-align: center;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.4px;
}

.risk-low {
  background: rgba(76, 183, 183, 0.15);
  color: #4cb7b7;
}

.risk-mid {
  background: rgba(255, 183, 77, 0.2);
  color: #f5a623;
}

.risk-high {
  background: rgba(255, 138, 128, 0.2);
  color: #ff8a80;
}

.risk-unknown {
  background: #eef1f3;
  color: #888;
}

.muted {
  color: #777;
  font-weight: 700;
}

.divider {
  color: #b2b2b2;
}

.patient-empty {
  padding: 16px 8px;
  text-align: center;
  color: #777;
  font-weight: 800;
}

.patient-sheet__footer {
  padding: 12px 16px 14px;
  background: #f5f6f7;
  box-shadow: inset 0 1px 0 rgba(0, 0, 0, 0.04);
}

.patient-sheet__hint {
  font-size: 13px;
  font-weight: 800;
  color: #2e2e2e;
}

/* 트랜지션 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.sheet-fade-enter-active,
.sheet-fade-leave-active {
  transition: opacity 0.18s ease;
}

.sheet-fade-enter-from,
.sheet-fade-leave-to {
  opacity: 0;
}

.sheet-up-enter-active,
.sheet-up-leave-active {
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.sheet-up-enter-from,
.sheet-up-leave-to {
  transform: translateY(14px);
  opacity: 0;
}
</style>
