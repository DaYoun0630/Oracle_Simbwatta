<script setup>
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import CaregiverShell from '@/components/shells/CaregiverShell.vue';
import DoctorShell from '@/components/shells/DoctorShell.vue';

const authStore = useAuthStore();
const role = computed(() => authStore.role);
const userName = computed(() => authStore.userName);
const router = useRouter();

const roleLabel = computed(() => {
  if (role.value === 'doctor') return '의료진 계정';
  if (role.value === 'caregiver') return '보호자 계정';
  return '이용자 계정';
});

const handleLogout = () => {
  authStore.clear();
  router.push({ name: 'landing' });
};
</script>

<template>
  <CaregiverShell v-if="role === 'caregiver'" title="내 정보">
    <div class="profile-container">
      <section class="user-info-card">
        <div class="avatar-placeholder"></div>
        <div class="details">
          <h2>{{ userName }} 님</h2>
          <p>{{ roleLabel }}</p>
        </div>
      </section>

      <section class="settings-list">
        <button class="setting-item">개인정보 수정</button>
        <button class="setting-item">알림 설정</button>
        <button class="setting-item logout" @click="handleLogout">로그아웃</button>
      </section>
    </div>
  </CaregiverShell>

  <DoctorShell v-else-if="role === 'doctor'" title="내 정보">
    <div class="profile-container">
      <section class="user-info-card">
        <div class="avatar-placeholder"></div>
        <div class="details">
          <h2>{{ userName }} 님</h2>
          <p>{{ roleLabel }}</p>
        </div>
      </section>

      <section class="settings-list">
        <button class="setting-item">개인정보 수정</button>
        <button class="setting-item">알림 설정</button>
        <button class="setting-item logout" @click="handleLogout">로그아웃</button>
      </section>
    </div>
  </DoctorShell>
</template>

<style scoped>
.profile-container {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.user-info-card {
  display: flex;
  align-items: center;
  gap: 20px;
  background: #ffffff;
  padding: 24px;
  border-radius: 24px;
  box-shadow: 10px 10px 20px #d1d9e6, -10px -10px 20px #ffffff;
}

.avatar-placeholder {
  width: 64px;
  height: 64px;
  background: #e0e5ec;
  border-radius: 50%;
  box-shadow: inset 4px 4px 8px #d1d9e6;
}

.details h2 {
  font-size: 18px;
  font-weight: 800;
}

.details p {
  font-size: 13px;
  color: #4cb7b7;
  font-weight: 700;
}

.settings-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.setting-item {
  background: #f5f6f7;
  padding: 16px 20px;
  border: none;
  border-radius: 16px;
  text-align: left;
  font-size: 14px;
  font-weight: 700;
  box-shadow: 4px 4px 8px #d1d9e6, -4px -4px 8px #ffffff;
  cursor: pointer;
  transition: transform 0.2s;
}

.setting-item:active {
  transform: scale(0.98);
}

.setting-item.logout {
  color: #ff8a80;
  margin-top: 20px;
}
</style>