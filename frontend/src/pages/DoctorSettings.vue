<script setup>
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import AppShell from '@/components/AppShell.vue';

const router = useRouter();
const authStore = useAuthStore();

const doctorName = computed(() => authStore.user?.name || authStore.userName || '미등록');
const profileImageUrl = computed(
  () => authStore.user?.profileImageUrl
    || authStore.user?.profile_image_url
    || localStorage.getItem('doctor-profile-image-url')
    || localStorage.getItem('user-avatar')
    || ''
);
const email = computed(() => authStore.user?.email || localStorage.getItem('doctor-email') || '미등록');

const phoneNumber = ref(localStorage.getItem('doctor-phone-number') || localStorage.getItem('user-phone') || '');
const dateOfBirth = ref(localStorage.getItem('doctor-date-of-birth') || authStore.user?.dateOfBirth || '');

const department = ref(localStorage.getItem('doctor-department') || localStorage.getItem('doctor-specialty') || '');
const isenseNumber = ref(localStorage.getItem('doctor-isense-number') || localStorage.getItem('doctor-license') || '');
const hospital = ref(localStorage.getItem('doctor-hospital') || localStorage.getItem('doctor-hospital-name') || '');
const hospitalNumber = ref(localStorage.getItem('doctor-hospital-number') || localStorage.getItem('doctor-hospital-phone') || '');

const showIsenseNumber = ref(false);
const saveMessage = ref('');

const avatarFallback = computed(() => doctorName.value?.trim()?.charAt(0) || '의');

const maskedIsenseNumber = computed(() => {
  if (!isenseNumber.value) {
    return '미등록';
  }

  if (showIsenseNumber.value) {
    return isenseNumber.value;
  }

  const number = isenseNumber.value;
  if (number.length <= 2) {
    return `${number.charAt(0)}*`;
  }

  return `${number.slice(0, 2)}${'*'.repeat(number.length - 2)}`;
});

const saveSettings = () => {
  localStorage.setItem('doctor-phone-number', phoneNumber.value.trim());
  localStorage.setItem('doctor-date-of-birth', dateOfBirth.value);

  localStorage.setItem('doctor-department', department.value.trim());
  localStorage.setItem('doctor-isense-number', isenseNumber.value.trim());
  localStorage.setItem('doctor-hospital', hospital.value.trim());
  localStorage.setItem('doctor-hospital-number', hospitalNumber.value.trim());

  // 기존 키와 호환 유지
  localStorage.setItem('doctor-specialty', department.value.trim());
  localStorage.setItem('doctor-license', isenseNumber.value.trim());
  localStorage.setItem('doctor-hospital-name', hospital.value.trim());
  localStorage.setItem('doctor-hospital-phone', hospitalNumber.value.trim());

  saveMessage.value = '저장되었습니다.';
  setTimeout(() => {
    saveMessage.value = '';
  }, 2000);
};

const handleLogout = () => {
  authStore.clear();
  router.push({ name: 'landing' });
};
</script>

<template>
  <AppShell title="의료진 설정" :showBack="true" :showMenu="false">
    <div class="doctor-settings">
      <section class="setting-card">
        <div class="profile-row">
          <div
            class="avatar"
            :style="profileImageUrl ? { backgroundImage: `url(${profileImageUrl})` } : {}"
            :aria-label="`${doctorName} 프로필 이미지`"
          >
            <span v-if="!profileImageUrl">{{ avatarFallback }}</span>
          </div>
          <div class="profile-text">
            <h3>{{ doctorName }}</h3>
            <p>{{ email }}</p>
          </div>
        </div>
        <div class="summary-grid">
          <div class="summary-item">
            <span>개인 연락처</span>
            <strong>{{ phoneNumber || '미등록' }}</strong>
          </div>
          <div class="summary-item" v-if="dateOfBirth">
            <span>생년월일</span>
            <strong>{{ dateOfBirth }}</strong>
          </div>
        </div>
      </section>

      <section class="setting-card">
        <div class="card-header">
          <div>
            <h3>의료진 정보</h3>
            <p>개인 페이지에 필요한 정보만 표시합니다.</p>
          </div>
        </div>

        <div class="input-grid">
          <div class="input-group">
            <label>진료과</label>
            <input v-model="department" type="text" placeholder="진료과를 입력하세요" />
          </div>

          <div class="input-group">
            <label>면허번호(ISENSE)</label>
            <input v-model="isenseNumber" type="text" placeholder="면허번호를 입력하세요" />
            <div class="inline-row">
              <strong class="masked-value">표시값: {{ maskedIsenseNumber }}</strong>
              <button class="text-button" @click="showIsenseNumber = !showIsenseNumber">
                {{ showIsenseNumber ? '가리기' : '전체보기' }}
              </button>
            </div>
          </div>

          <div class="input-group">
            <label>병원명</label>
            <input v-model="hospital" type="text" placeholder="소속 병원명을 입력하세요" />
          </div>

          <div class="input-group">
            <label>병원 대표번호</label>
            <input v-model="hospitalNumber" type="tel" placeholder="02-0000-0000" />
          </div>
        </div>
      </section>

      <section class="setting-card">
        <div class="card-header">
          <div>
            <h3>개인 연락 정보</h3>
            <p>본인 확인 또는 연락을 위해서만 사용됩니다.</p>
          </div>
        </div>

        <div class="input-grid">
          <div class="input-group">
            <label>개인 연락처</label>
            <input v-model="phoneNumber" type="tel" placeholder="010-0000-0000" />
          </div>

          <div class="input-group">
            <label>생년월일 (선택)</label>
            <input v-model="dateOfBirth" type="date" />
          </div>
        </div>
      </section>

      <button class="primary-btn" @click="saveSettings">저장하기</button>
      <p v-if="saveMessage" class="save-message">{{ saveMessage }}</p>

      <button class="logout-text-button" @click="handleLogout">로그아웃</button>
    </div>
  </AppShell>
</template>

<style scoped>
.doctor-settings {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-bottom: 28px;
  min-height: calc(100vh - 140px);
}

.setting-card {
  background: #f5f6f7;
  padding: 22px;
  border-radius: 26px;
  box-shadow: 14px 14px 28px #cfd6df, -14px -14px 28px #ffffff;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.profile-row {
  display: flex;
  gap: 14px;
  align-items: center;
}

.avatar {
  width: 70px;
  height: 70px;
  border-radius: 50%;
  background: #dfe6ec;
  background-position: center;
  background-size: cover;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #2e2e2e;
  font-size: 28px;
  font-weight: 800;
  box-shadow: inset 4px 4px 10px rgba(209, 217, 230, 0.65), inset -4px -4px 10px #ffffff;
}

.profile-text h3 {
  margin: 0;
  font-size: 21px;
  font-weight: 800;
  color: #2e2e2e;
}

.profile-text p {
  margin: 4px 0 0;
  font-size: 14px;
  font-weight: 700;
  color: #707070;
  word-break: break-all;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.summary-item {
  background: #ffffff;
  border-radius: 16px;
  padding: 12px;
  box-shadow: inset 4px 4px 8px rgba(209, 217, 230, 0.65), inset -4px -4px 8px #ffffff;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-item span {
  font-size: 13px;
  font-weight: 700;
  color: #7a7a7a;
}

.summary-item strong {
  font-size: 16px;
  font-weight: 800;
  color: #2e2e2e;
}

.card-header h3 {
  font-size: 19px;
  font-weight: 800;
  margin: 0 0 4px;
  color: #2e2e2e;
}

.card-header p {
  font-size: 14px;
  font-weight: 700;
  color: #777;
  margin: 0;
}

.input-grid {
  display: grid;
  gap: 14px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.input-group label {
  font-size: 14px;
  font-weight: 800;
  color: #2e2e2e;
}

.input-group input {
  width: 100%;
  padding: 14px 16px;
  border-radius: 16px;
  border: none;
  background: #ffffff;
  box-shadow: inset 4px 4px 8px rgba(209, 217, 230, 0.65), inset -4px -4px 8px #ffffff;
  font-size: 15px;
  font-weight: 700;
  color: #2e2e2e;
  outline: none;
  box-sizing: border-box;
}

.inline-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.masked-value {
  font-size: 13px;
  font-weight: 800;
  color: #4c7d7d;
}

.text-button {
  border: none;
  background: transparent;
  color: #4cb7b7;
  font-size: 13px;
  font-weight: 800;
  padding: 0;
  cursor: pointer;
}

.primary-btn {
  padding: 14px 18px;
  border: none;
  border-radius: 16px;
  background: #4cb7b7;
  color: #ffffff;
  font-size: 16px;
  font-weight: 800;
  cursor: pointer;
  box-shadow: 0 8px 16px rgba(76, 183, 183, 0.3);
}

.save-message {
  margin: -8px 0 0;
  color: #4c7d7d;
  font-size: 13px;
  font-weight: 800;
  text-align: center;
}

.logout-text-button {
  background: none;
  border: none;
  font-size: 16px;
  font-weight: 800;
  color: #ff8a80;
  padding: 12px;
  cursor: pointer;
  margin-top: auto;
  transition: opacity 0.2s;
}

.logout-text-button:hover {
  opacity: 0.8;
}

@media (max-width: 520px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .inline-row {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
