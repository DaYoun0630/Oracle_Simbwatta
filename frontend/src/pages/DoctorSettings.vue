<script setup>
import { ref, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { updateAuthProfile } from '@/api/settings';
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

const phoneNumber = ref(
  authStore.user?.phone_number
  || authStore.user?.phoneNumber
  || localStorage.getItem('doctor-phone-number')
  || localStorage.getItem('user-phone')
  || ''
);
const dateOfBirth = ref(
  authStore.user?.date_of_birth
  || authStore.user?.dateOfBirth
  || localStorage.getItem('doctor-date-of-birth')
  || ''
);

const department = ref(
  authStore.user?.department
  || localStorage.getItem('doctor-department')
  || localStorage.getItem('doctor-specialty')
  || ''
);
const isenseNumber = ref(
  authStore.user?.license_number
  || localStorage.getItem('doctor-isense-number')
  || localStorage.getItem('doctor-license')
  || ''
);
const hospital = ref(
  authStore.user?.hospital
  || localStorage.getItem('doctor-hospital')
  || localStorage.getItem('doctor-hospital-name')
  || ''
);
const hospitalNumber = ref(
  authStore.user?.hospital_number
  || localStorage.getItem('doctor-hospital-number')
  || localStorage.getItem('doctor-hospital-phone')
  || ''
);

const showIsenseNumber = ref(false);
const saveMessage = ref('');
const currentYear = new Date().getFullYear();
const birthYear = ref('');
const birthMonth = ref('');
const birthDay = ref('');

const availableYears = computed(() =>
  Array.from({ length: 120 }, (_, index) => String(currentYear - 1 - index))
);

const isValidBirthYear = computed(() => {
  if (!/^\d{4}$/.test(birthYear.value)) return false;
  const year = Number(birthYear.value);
  return year >= 1900 && year < currentYear;
});

const monthOptions = computed(() =>
  Array.from({ length: 12 }, (_, index) => String(index + 1).padStart(2, '0'))
);

const dayOptions = computed(() => {
  if (!isValidBirthYear.value || !birthMonth.value) return [];
  const daysInMonth = new Date(Number(birthYear.value), Number(birthMonth.value), 0).getDate();
  return Array.from({ length: daysInMonth }, (_, index) => String(index + 1).padStart(2, '0'));
});

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

const formatPersonalPhoneNumber = (input) => {
  let digits = String(input ?? '').replace(/\D/g, '');

  if (!digits.startsWith('010')) {
    digits = `010${digits.replace(/^010/, '')}`;
  }

  digits = digits.slice(0, 11);
  const body = digits.slice(3);

  if (body.length <= 4) {
    return `010-${body}`;
  }

  return `010-${body.slice(0, 4)}-${body.slice(4, 8)}`;
};

const formatHospitalPhoneNumber = (input) => {
  const digits = String(input ?? '').replace(/\D/g, '').slice(0, 10);

  if (digits.length <= 2) {
    return digits;
  }

  if (digits.length <= 6) {
    return `${digits.slice(0, 2)}-${digits.slice(2)}`;
  }

  return `${digits.slice(0, 2)}-${digits.slice(2, 6)}-${digits.slice(6)}`;
};

const onPersonalPhoneFocus = () => {
  if (!phoneNumber.value.trim()) {
    phoneNumber.value = '010-';
    return;
  }

  phoneNumber.value = formatPersonalPhoneNumber(phoneNumber.value);
};

const onPersonalPhoneInput = () => {
  phoneNumber.value = formatPersonalPhoneNumber(phoneNumber.value);
};

const onHospitalPhoneInput = () => {
  hospitalNumber.value = formatHospitalPhoneNumber(hospitalNumber.value);
};

const onBirthYearInput = () => {
  birthYear.value = birthYear.value.replace(/\D/g, '').slice(0, 4);

  if (!isValidBirthYear.value) {
    birthMonth.value = '';
    birthDay.value = '';
  }
};

const syncBirthDateFromParts = () => {
  if (isValidBirthYear.value && birthMonth.value && birthDay.value) {
    dateOfBirth.value = `${birthYear.value}-${birthMonth.value}-${birthDay.value}`;
    return;
  }

  dateOfBirth.value = '';
};

const initBirthParts = () => {
  if (!dateOfBirth.value) return;

  const match = String(dateOfBirth.value).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) {
    dateOfBirth.value = '';
    return;
  }

  birthYear.value = match[1];
  birthMonth.value = match[2];
  birthDay.value = match[3];

  if (!isValidBirthYear.value || !monthOptions.value.includes(birthMonth.value) || !dayOptions.value.includes(birthDay.value)) {
    birthYear.value = '';
    birthMonth.value = '';
    birthDay.value = '';
    dateOfBirth.value = '';
  }
};

watch([birthYear, birthMonth, birthDay], () => {
  if (birthDay.value && !dayOptions.value.includes(birthDay.value)) {
    birthDay.value = '';
  }

  syncBirthDateFromParts();
});

phoneNumber.value = phoneNumber.value ? formatPersonalPhoneNumber(phoneNumber.value) : '';
hospitalNumber.value = hospitalNumber.value ? formatHospitalPhoneNumber(hospitalNumber.value) : '';
initBirthParts();

const saveSettings = async () => {
  const phone = phoneNumber.value.trim();
  const dob = dateOfBirth.value || null;
  const dept = department.value.trim();
  const license = isenseNumber.value.trim();
  const hospitalName = hospital.value.trim();
  const hospitalPhone = hospitalNumber.value.trim();

  localStorage.setItem('doctor-phone-number', phone);
  localStorage.setItem('doctor-date-of-birth', dob || '');
  localStorage.setItem('doctor-department', dept);
  localStorage.setItem('doctor-isense-number', license);
  localStorage.setItem('doctor-hospital', hospitalName);
  localStorage.setItem('doctor-hospital-number', hospitalPhone);
  localStorage.setItem('doctor-specialty', dept);
  localStorage.setItem('doctor-license', license);
  localStorage.setItem('doctor-hospital-name', hospitalName);
  localStorage.setItem('doctor-hospital-phone', hospitalPhone);

  try {
    if (authStore.token) {
      const updatedUser = await updateAuthProfile(authStore.token, {
        phone_number: phone || null,
        date_of_birth: dob,
        department: dept || null,
        license_number: license || null,
        hospital: hospitalName || null,
        hospital_number: hospitalPhone || null,
      });
      authStore.setUser({
        ...(authStore.user || {}),
        ...updatedUser,
      });
    } else if (authStore.user) {
      authStore.setUser({
        ...authStore.user,
        phone_number: phone || null,
        date_of_birth: dob,
        department: dept || null,
        license_number: license || null,
        hospital: hospitalName || null,
        hospital_number: hospitalPhone || null,
      });
    }

    saveMessage.value = '저장되었습니다.';
  } catch (error) {
    console.error('Failed to save doctor settings:', error);
    saveMessage.value = error instanceof Error ? `저장 실패: ${error.message}` : '저장에 실패했습니다.';
  }

  setTimeout(() => {
    saveMessage.value = '';
  }, 2200);
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
            <p>개인 페이지에 필요한 정보만 표시됩니다.</p>
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
              <strong class="masked-value">표시값 {{ maskedIsenseNumber }}</strong>
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
            <label>병원 대표전화번호</label>
            <input
              v-model="hospitalNumber"
              type="tel"
              placeholder="02-0000-0000"
              @input="onHospitalPhoneInput"
            />
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
            <input
              v-model="phoneNumber"
              type="tel"
              placeholder="010-0000-0000"
              @focus="onPersonalPhoneFocus"
              @input="onPersonalPhoneInput"
            />
          </div>

          <div class="input-group">
            <label>생년월일 (선택)</label>
            <div class="birthdate-row">
              <input
                v-model="birthYear"
                type="text"
                inputmode="numeric"
                maxlength="4"
                placeholder="연도(YYYY)"
                list="doctor-birth-year-options"
                @input="onBirthYearInput"
              />
              <datalist id="doctor-birth-year-options">
                <option v-for="year in availableYears" :key="year" :value="year"></option>
              </datalist>
              <select v-model="birthMonth" :disabled="!isValidBirthYear">
                <option value="">월</option>
                <option v-for="month in monthOptions" :key="month" :value="month">{{ month }}</option>
              </select>
              <select v-model="birthDay" :disabled="!isValidBirthYear || !birthMonth">
                <option value="">일</option>
                <option v-for="day in dayOptions" :key="day" :value="day">{{ day }}</option>
              </select>
            </div>
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

.input-group input,
.input-group select {
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

.birthdate-row {
  display: grid;
  grid-template-columns: 1.5fr 1fr 1fr;
  gap: 8px;
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

  .birthdate-row {
    grid-template-columns: 1fr;
  }
}
</style>
