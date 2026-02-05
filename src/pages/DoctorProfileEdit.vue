<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import AppShell from '@/components/AppShell.vue';

const router = useRouter();
const authStore = useAuthStore();

const doctorName = ref(authStore.userName);
const licenseNumber = ref(localStorage.getItem('doctor-license') || '');
const specialty = ref(localStorage.getItem('doctor-specialty') || '');
const contact = ref(localStorage.getItem('doctor-contact') || '');

const saveProfile = () => {
  localStorage.setItem('doctor-license', licenseNumber.value);
  localStorage.setItem('doctor-specialty', specialty.value);
  localStorage.setItem('doctor-contact', contact.value);
  router.back();
};
</script>

<template>
  <AppShell title="의료진 프로필 수정" :showBack="true" :showMenu="false">
    <div class="profile-edit">
      <section class="card">
        <h3>기본 정보</h3>
        <div class="input-group">
          <label>의료진 이름</label>
          <input v-model="doctorName" type="text" disabled />
        </div>
        <div class="input-group">
          <label>면허 번호</label>
          <input v-model="licenseNumber" type="text" placeholder="면허 번호를 입력하세요" />
        </div>
        <div class="input-group">
          <label>전문 분야</label>
          <input v-model="specialty" type="text" placeholder="전문 분야를 입력하세요" />
        </div>
        <div class="input-group">
          <label>연락처</label>
          <input v-model="contact" type="text" placeholder="010-0000-0000" />
        </div>
      </section>

      <button class="save-btn" @click="saveProfile">저장하기</button>
    </div>
  </AppShell>
</template>

<style scoped>
.profile-edit {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding-bottom: 32px;
  font-size: 16px;
}

.card {
  background: #f5f6f7;
  padding: 24px;
  border-radius: 28px;
  box-shadow: 14px 14px 28px #cfd6df, -14px -14px 28px #ffffff;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card h3 {
  font-size: 20px;
  font-weight: 800;
  margin: 0;
  color: #2e2e2e;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-group label {
  font-size: 16px;
  font-weight: 800;
  color: #2e2e2e;
}

.input-group input {
  width: 100%;
  padding: 18px 20px;
  border-radius: 20px;
  border: none;
  background: #ffffff;
  box-shadow: inset 4px 4px 10px #d1d9e6, inset -4px -4px 10px #ffffff;
  font-size: 16px;
  font-weight: 700;
  color: #2e2e2e;
  outline: none;
}

.input-group input:disabled {
  color: #888;
}

.save-btn {
  width: 100%;
  padding: 18px;
  border: none;
  border-radius: 24px;
  background: #4cb7b7;
  box-shadow: 0 10px 20px rgba(76, 183, 183, 0.3);
  font-size: 18px;
  font-weight: 800;
  color: #ffffff;
  cursor: pointer;
}
</style>
