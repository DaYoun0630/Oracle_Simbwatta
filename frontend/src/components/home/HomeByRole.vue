<script setup>
import SubjectHome from './SubjectHome.vue';
import CaregiverHome from './CaregiverHome.vue';
import DoctorHome from './DoctorHome.vue';

const props = defineProps({
  role: {
    type: String,
    required: true
  }
});
</script>

<template>
  <SubjectHome v-if="role === 'subject'" />
  <CaregiverHome v-else-if="role === 'caregiver'" />
  <DoctorHome v-else-if="role === 'doctor'" />
  <div v-else class="empty-state">
    잘못된 역할 값입니다: {{ role }}
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
  font-weight: 800;
  color: #888;
}
</style>