<script setup>
import { ref, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import AppShell from '@/components/AppShell.vue';

const router = useRouter();
const authStore = useAuthStore();

const doctorName = computed(() => authStore.userName);

const licenseNumber = ref(localStorage.getItem('doctor-license') || '');
const specialty = ref(localStorage.getItem('doctor-specialty') || '');
const contact = ref(localStorage.getItem('doctor-contact') || '');

const hospitalName = ref(localStorage.getItem('doctor-hospital-name') || '');
const hospitalDepartment = ref(localStorage.getItem('doctor-hospital-dept') || '');
const hospitalPhone = ref(localStorage.getItem('doctor-hospital-phone') || '');

const emergencyAlert = ref(localStorage.getItem('doctor-alert-emergency') !== 'off');
const riskThreshold = ref(Number(localStorage.getItem('doctor-alert-threshold') || 70));

const goToProfileEdit = () => {
  router.push({ name: 'doctor-profile-edit' });
};

const goToNotifications = () => {
  router.push({ name: 'doctor-notification' });
};

const handleLogout = () => {
  authStore.clear();
  router.push({ name: 'landing' });
};

const saveHospitalInfo = () => {
  localStorage.setItem('doctor-hospital-name', hospitalName.value);
  localStorage.setItem('doctor-hospital-dept', hospitalDepartment.value);
  localStorage.setItem('doctor-hospital-phone', hospitalPhone.value);
};

watch(emergencyAlert, (value) => {
  localStorage.setItem('doctor-alert-emergency', value ? 'on' : 'off');
});

watch(riskThreshold, (value) => {
  localStorage.setItem('doctor-alert-threshold', String(value));
});
</script>

<template>
  <AppShell title="의료진 설정" :showBack="true" :showMenu="false">
    <div class="doctor-settings">
      <section class="setting-card">
        <div class="card-header">
          <div>
            <h3>의료진 프로필</h3>
            <p>{{ doctorName }} 님의 전문 정보</p>
          </div>
          <button class="primary-btn" @click="goToProfileEdit">프로필 수정</button>
        </div>
        <div class="info-grid">
          <div class="info-item">
            <span>면허 번호</span>
            <strong>{{ licenseNumber || '미등록' }}</strong>
          </div>
          <div class="info-item">
            <span>전문 분야</span>
            <strong>{{ specialty || '미등록' }}</strong>
          </div>
          <div class="info-item">
            <span>연락처</span>
            <strong>{{ contact || '미등록' }}</strong>
          </div>
        </div>
      </section>

      <section class="setting-card">
        <div class="card-header">
          <div>
            <h3>변화 알림 설정</h3>
            <p>환자 변화 추세를 요약 알림으로 확인</p>
          </div>
          <button class="toggle" :class="{ on: emergencyAlert }" @click="emergencyAlert = !emergencyAlert">
            <span class="knob"></span>
          </button>
        </div>
        <div class="threshold">
          <label>위험도 임계값</label>
          <input v-model="riskThreshold" type="range" min="40" max="90" step="5" />
          <span class="threshold-value">{{ riskThreshold }}점</span>
        </div>
        <button class="ghost-btn" @click="goToNotifications">알림 상세 설정</button>
      </section>

      <section class="setting-card">
        <div class="card-header">
          <div>
            <h3>소속 병원 정보</h3>
            <p>임상 협업용 기관 정보 관리</p>
          </div>
          <button class="primary-btn" @click="saveHospitalInfo">저장</button>
        </div>
        <div class="input-grid">
          <div class="input-group">
            <label>병원명</label>
            <input v-model="hospitalName" type="text" placeholder="병원명을 입력하세요" />
          </div>
          <div class="input-group">
            <label>진료과</label>
            <input v-model="hospitalDepartment" type="text" placeholder="전문의 과를 입력하세요" />
          </div>
          <div class="input-group">
            <label>대표 연락처</label>
            <input v-model="hospitalPhone" type="text" placeholder="02-0000-0000" />
          </div>
        </div>
      </section>

      <button class="logout-text-button" @click="handleLogout">
        로그아웃
      </button>
    </div>
  </AppShell>
</template>

<style scoped>
.doctor-settings {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding-bottom: 32px;
  min-height: calc(100vh - 140px);
  font-size: 16px;
}

.setting-card {
  background: #f5f6f7;
  padding: 24px;
  border-radius: 28px;
  box-shadow: 14px 14px 28px #cfd6df, -14px -14px 28px #ffffff;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.card-header h3 {
  font-size: 20px;
  font-weight: 800;
  margin: 0 0 6px;
  color: #2e2e2e;
}

.card-header p {
  font-size: 16px;
  font-weight: 700;
  color: #777;
  margin: 0;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.info-item {
  background: #ffffff;
  border-radius: 18px;
  padding: 14px;
  box-shadow: inset 4px 4px 8px rgba(209, 217, 230, 0.6), inset -4px -4px 8px #ffffff;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.info-item span {
  font-size: 16px;
  font-weight: 700;
  color: #888;
}

.info-item strong {
  font-size: 18px;
  font-weight: 800;
  color: #2e2e2e;
}

.primary-btn {
  padding: 12px 18px;
  border: none;
  border-radius: 16px;
  background: #4cb7b7;
  color: #ffffff;
  font-size: 16px;
  font-weight: 800;
  cursor: pointer;
  box-shadow: 0 8px 16px rgba(76, 183, 183, 0.3);
}

.ghost-btn {
  border: none;
  background: #ffffff;
  color: #4cb7b7;
  font-size: 16px;
  font-weight: 800;
  padding: 14px 18px;
  border-radius: 18px;
  cursor: pointer;
  box-shadow: inset 4px 4px 8px rgba(209, 217, 230, 0.6), inset -4px -4px 8px #ffffff;
}

.toggle {
  width: 64px;
  height: 36px;
  border-radius: 999px;
  border: none;
  background: #dfe6ec;
  position: relative;
  cursor: pointer;
  transition: background 0.2s ease;
}

.toggle .knob {
  position: absolute;
  top: 4px;
  left: 4px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #ffffff;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
  transition: transform 0.2s ease;
}

.toggle.on {
  background: #4cb7b7;
}

.toggle.on .knob {
  transform: translateX(28px);
}

.threshold {
  display: grid;
  gap: 10px;
}

.threshold label {
  font-size: 16px;
  font-weight: 800;
  color: #2e2e2e;
}

.threshold input {
  width: 100%;
  height: 12px;
  appearance: none;
  background: #e0e5ec;
  border-radius: 999px;
  outline: none;
}

.threshold input::-webkit-slider-thumb {
  appearance: none;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #4cb7b7;
  box-shadow: 0 4px 10px rgba(76, 183, 183, 0.4);
}

.threshold input::-moz-range-thumb {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #4cb7b7;
  border: none;
}

.threshold-value {
  font-size: 16px;
  font-weight: 800;
  color: #4cb7b7;
}

.input-grid {
  display: grid;
  gap: 16px;
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
  padding: 16px 18px;
  border-radius: 18px;
  border: none;
  background: #ffffff;
  box-shadow: inset 4px 4px 8px rgba(209, 217, 230, 0.6), inset -4px -4px 8px #ffffff;
  font-size: 16px;
  font-weight: 700;
  color: #2e2e2e;
  outline: none;
}

.logout-text-button {
  background: none;
  border: none;
  font-size: 18px;
  font-weight: 800;
  color: #ff8a80;
  padding: 16px;
  cursor: pointer;
  margin-top: auto;
  transition: opacity 0.2s;
}

.logout-text-button:hover {
  opacity: 0.8;
}

@media (max-width: 520px) {
  .card-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }
}
</style>
