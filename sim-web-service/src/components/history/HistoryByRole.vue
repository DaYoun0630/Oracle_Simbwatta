<script setup>
import SubjectHistory from "./SubjectHistory.vue";
import CaregiverHistory from "./CaregiverHistory.vue";
import DoctorHistory from "./DoctorHistory.vue";

const props = defineProps({
  role: {
    type: String,
    required: true
  },
  currentTab: {
    type: String,
    default: 'clinical'
  },
  doctorData: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  }
});
</script>

<template>
  <SubjectHistory v-if="role === 'subject'" />
  <CaregiverHistory v-else-if="role === 'caregiver'" />
  <DoctorHistory v-else-if="role === 'doctor'" :currentTab="currentTab" :data="doctorData" :loading="loading" />
  <div v-else class="empty-state">
    <p>사용자 정보를 확인하고 있습니다.</p>
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
  text-align: center;
  font-weight: 800;
  color: #888;
}
</style>
