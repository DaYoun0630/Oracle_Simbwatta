<script setup>
import { computed, onMounted, watch } from 'vue'; // 역할별 상태와 라우트 동기화를 처리한다
import { useRoute } from 'vue-router'; // 환자 선택 쿼리를 읽는다
import { useAuthStore } from '@/stores/auth'; // 인증 상태를 가져온다
import CaregiverShell from '@/components/shells/CaregiverShell.vue';
import DoctorShell from '@/components/shells/DoctorShell.vue';
import SubjectHome from '@/components/home/SubjectHome.vue';
import CaregiverHome from '@/components/home/CaregiverHome.vue';
import DoctorHome from '@/components/home/DoctorHome.vue';
import { useDoctorData } from '@/composables/useDoctorData';

const authStore = useAuthStore(); // 인증 상태를 사용한다
const route = useRoute(); // 현재 라우트를 읽는다
const userRole = computed(() => authStore.role); // 현재 역할을 계산한다

const {
  data: doctorData,
  loading: doctorLoading,
  fetchData: fetchDoctorData,
  switchPatient,
  currentPatientId
} = useDoctorData();

// 라우트 쿼리에서 환자 ID를 읽는다
const getRoutePatientId = () => {
  const rawParam = route.params?.patientId;
  const paramValue = typeof rawParam === 'string' ? rawParam : null;
  const rawQuery = route.query.patientId;
  const queryValue = typeof rawQuery === 'string' ? rawQuery : null;
  return paramValue || queryValue;
};

onMounted(() => {
  if (userRole.value === 'doctor') {
    fetchDoctorData(getRoutePatientId() || currentPatientId.value);
  }
});

// 환자 상세 URL 변경에 맞춰 데이터를 동기화한다
watch(() => route.params?.patientId || route.query.patientId, (value) => {
  if (userRole.value !== 'doctor') return;
  if (typeof value === 'string' && value !== currentPatientId.value) {
    switchPatient(value);
  }
});

const handlePatientChange = (patientId) => {
  switchPatient(patientId);
};

const handleTabChange = (tabName) => {
  console.log('Tab changed:', tabName);
};
</script>

<template>
  <div>
    <SubjectHome v-if="userRole === 'subject'" />

    <CaregiverShell v-else-if="userRole === 'caregiver'" title="모니터링 홈">
      <CaregiverHome />
    </CaregiverShell>

    <DoctorShell 
      v-else-if="userRole === 'doctor'" 
      title="환자 상세"
      :patients="doctorData?.patients || []"
      :currentPatientId="doctorData?.currentPatient?.id"
      @patient-change="handlePatientChange"
      @tab-change="handleTabChange"
    >
      <template #default="{ currentTab, openPatientSheet, isPatientSheetOpen }">
        <DoctorHome
          :doctorData="doctorData"
          :loading="doctorLoading"
          :currentTab="currentTab"
          :openPatientSheet="openPatientSheet"
          :isPatientSheetOpen="isPatientSheetOpen"
        />
      </template>
    </DoctorShell>

    <div v-else class="error-state">
      <p>역할 정보를 확인할 수 없습니다.</p>
    </div>
  </div>
</template>

<style scoped>
.error-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  font-size: 1rem;
  font-weight: 800;
  color: #888;
}
</style>
