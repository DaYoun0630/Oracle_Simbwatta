<script setup>
import { computed, onMounted, onUnmounted, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import SubjectShell from '@/components/shells/SubjectShell.vue';
import CaregiverShell from '@/components/shells/CaregiverShell.vue';
import DoctorShell from '@/components/shells/DoctorShell.vue';
import HistoryByRole from '@/components/history/HistoryByRole.vue';
import { useDoctorData } from '@/composables/useDoctorData';

const authStore = useAuthStore();
const role = computed(() => authStore.role);

const pageTitles = {
  subject: '나의 발자취',
  caregiver: '인지 건강 기록',
  doctor: '환자 리포트'
};

const title = computed(() => pageTitles[role.value] || pageTitles.subject);

const router = useRouter();
const route = useRoute();

const {
  data: doctorData,
  loading: doctorLoading,
  fetchData: fetchDoctorData,
  switchPatient,
  currentPatientId,
  startAutoRefresh,
  stopAutoRefresh,
} = useDoctorData();

const getRoutePatientId = () => {
  const paramId = route.params?.patientId;
  if (typeof paramId === 'string') return paramId;
  const queryId = route.query.patientId;
  return typeof queryId === 'string' ? queryId : null;
};

onMounted(() => {
  if (role.value === 'doctor') {
    const routePatientId = getRoutePatientId();
    fetchDoctorData(routePatientId || currentPatientId.value);
    startAutoRefresh();
  }
});

onUnmounted(() => {
  stopAutoRefresh();
});

watch(() => route.params?.patientId || route.query.patientId, (value) => {
  if (role.value !== 'doctor') return;
  if (typeof value === 'string' && value !== currentPatientId.value) {
    switchPatient(value);
  }
});

const handlePatientChange = (patientId) => {
  switchPatient(patientId);
  if (route.name === 'doctor-report') {
    router.replace({ name: route.name, params: { ...route.params, patientId }, query: route.query });
    return;
  }
  router.replace({ query: { ...route.query, patientId } });
};
</script>

<template>
  <div>
    <SubjectShell v-if="role === 'subject'" :title="title" :showHomeButton="true">
      <div class="history-page-container">
        <h1 class="page-title">{{ title }}</h1>
        <HistoryByRole :role="role" />
      </div>
    </SubjectShell>

    <CaregiverShell v-else-if="role === 'caregiver'" :title="title">
      <HistoryByRole :role="role" />
    </CaregiverShell>

    <DoctorShell 
      v-else-if="role === 'doctor'"
      :title="title"
      :patients="doctorData?.patients || []"
      :currentPatientId="doctorData?.currentPatient?.id"
      @patient-change="handlePatientChange"
    >
      <template #default="{ currentTab }">
        <HistoryByRole :role="role" :currentTab="currentTab" :doctorData="doctorData" :loading="doctorLoading" />
      </template>
    </DoctorShell>

    <div v-else class="error-state">
      <p>역할 정보를 확인할 수 없습니다.</p>
    </div>
  </div>
</template>

<style scoped>
.history-page-container {
  max-width: 460px;
  margin: 0 auto;
  padding: 32px 20px;
}

.page-title {
  font-size: 24px;
  font-weight: 900;
  color: #2e2e2e;
  margin-bottom: 24px;
  text-align: center;
}

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
