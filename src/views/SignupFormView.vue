<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import GenderSelect from "@/components/signup/GenderSelect.vue";
import RelationshipSelect from "@/components/signup/RelationshipSelect.vue";
import SubjectLinkInput from "@/components/signup/SubjectLinkInput.vue";
import DoctorFields from "@/components/signup/DoctorFields.vue";
import { useSignupStore } from "@/stores/signup";

interface FormErrors {
  name: string;
  email: string;
  phone_number: string;
  date_of_birth: string;
  password: string;
  passwordConfirm: string;
  gender: string;
  relationship: string;
  subject_link_code: string;
  department: string;
  license_number: string;
  hospital: string;
  hospital_number: string;
}

const router = useRouter();
const signupStore = useSignupStore();
const passwordConfirm = ref("");

const errors = reactive<FormErrors>({
  name: "",
  email: "",
  phone_number: "",
  date_of_birth: "",
  password: "",
  passwordConfirm: "",
  gender: "",
  relationship: "",
  subject_link_code: "",
  department: "",
  license_number: "",
  hospital: "",
  hospital_number: "",
});

const roleTitle = computed(() => signupStore.roleLabel);

const isNextEnabled = computed(() => {
  const hasPasswordConfirm = passwordConfirm.value.trim().length > 0;
  const isPasswordMatch = signupStore.password === passwordConfirm.value;
  return signupStore.canProceedToTerms && hasPasswordConfirm && isPasswordMatch;
});

const resetErrors = () => {
  (Object.keys(errors) as Array<keyof FormErrors>).forEach((key) => {
    errors[key] = "";
  });
};

const validateCommonFields = (): boolean => {
  let isValid = true;

  if (!signupStore.name.trim()) {
    errors.name = "이름을 입력해 주세요.";
    isValid = false;
  }

  if (!signupStore.email.trim()) {
    errors.email = "이메일을 입력해 주세요.";
    isValid = false;
  } else if (!signupStore.isEmailValid) {
    errors.email = "이메일 형식이 올바르지 않습니다.";
    isValid = false;
  }

  if (!signupStore.phone_number.trim()) {
    errors.phone_number = "전화번호를 입력해 주세요.";
    isValid = false;
  } else if (!signupStore.isPhoneValid) {
    errors.phone_number = "전화번호 형식이 올바르지 않습니다.";
    isValid = false;
  }

  if (!signupStore.date_of_birth.trim()) {
    errors.date_of_birth = "생년월일을 입력해 주세요.";
    isValid = false;
  }

  if (!signupStore.password.trim()) {
    errors.password = "비밀번호를 입력해 주세요.";
    isValid = false;
  } else if (!signupStore.isPasswordValid) {
    errors.password = "비밀번호는 8자 이상이어야 합니다.";
    isValid = false;
  }

  if (!passwordConfirm.value.trim()) {
    errors.passwordConfirm = "비밀번호 확인을 입력해 주세요.";
    isValid = false;
  } else if (signupStore.password !== passwordConfirm.value) {
    errors.passwordConfirm = "비밀번호가 일치하지 않습니다.";
    isValid = false;
  }

  return isValid;
};

const validateRoleSpecificFields = (): boolean => {
  let isValid = true;

  if (signupStore.role_code === 0) {
    if (!signupStore.gender) {
      errors.gender = "성별을 선택해 주세요.";
      isValid = false;
    }
  }

  if (signupStore.role_code === 1) {
    if (!signupStore.relationship) {
      errors.relationship = "대상자와의 관계를 선택해 주세요.";
      isValid = false;
    }

    if (!signupStore.subject_link_code.trim()) {
      errors.subject_link_code = "대상자 연동 코드를 입력해 주세요.";
      isValid = false;
    } else if (!signupStore.subjectCodeVerified) {
      errors.subject_link_code = "코드 확인 버튼으로 유효성 검증을 완료해 주세요.";
      isValid = false;
    }
  }

  if (signupStore.role_code === 2) {
    if (!signupStore.department.trim()) {
      errors.department = "진료과를 입력해 주세요.";
      isValid = false;
    }
    if (!signupStore.license_number.trim()) {
      errors.license_number = "면허번호를 입력해 주세요.";
      isValid = false;
    }
    if (!signupStore.hospital.trim()) {
      errors.hospital = "병원명을 입력해 주세요.";
      isValid = false;
    }
    if (!signupStore.hospital_number.trim()) {
      errors.hospital_number = "병원 연락처를 입력해 주세요.";
      isValid = false;
    }
  }

  return isValid;
};

const validateForm = (): boolean => {
  resetErrors();
  const commonValid = validateCommonFields();
  const roleValid = validateRoleSpecificFields();
  return commonValid && roleValid;
};

const goNext = () => {
  if (!validateForm()) return;
  router.push({ name: "signup-terms" });
};

const goBack = () => {
  router.push({ name: "signup-role" });
};

onMounted(() => {
  if (signupStore.role_code === null) {
    router.replace({ name: "signup-role" });
  }
});
</script>

<template>
  <main class="signup-page">
    <section class="signup-card">
      <p class="step-label">회원가입 2 / 4</p>
      <h1>{{ roleTitle }} 정보 입력</h1>
      <p class="description">필수 항목만 먼저 입력해 주세요. 입력 값은 다음 단계로 이동해도 유지됩니다.</p>

      <section class="section">
        <h2>기본 정보</h2>
        <div class="field-grid">
          <label class="field">
            <span>이름</span>
            <input v-model="signupStore.name" type="text" placeholder="이름 입력" />
            <small v-if="errors.name" class="error">{{ errors.name }}</small>
          </label>

          <label class="field">
            <span>이메일</span>
            <input v-model="signupStore.email" type="email" placeholder="example@email.com" />
            <small v-if="errors.email" class="error">{{ errors.email }}</small>
          </label>

          <label class="field">
            <span>전화번호</span>
            <input v-model="signupStore.phone_number" type="tel" placeholder="010-0000-0000" />
            <small v-if="errors.phone_number" class="error">{{ errors.phone_number }}</small>
          </label>

          <label class="field">
            <span>생년월일</span>
            <input v-model="signupStore.date_of_birth" type="date" />
            <small v-if="errors.date_of_birth" class="error">{{ errors.date_of_birth }}</small>
          </label>

          <label class="field">
            <span>비밀번호</span>
            <input v-model="signupStore.password" type="password" placeholder="8자 이상 입력" />
            <small v-if="errors.password" class="error">{{ errors.password }}</small>
          </label>

          <label class="field">
            <span>비밀번호 확인</span>
            <input v-model="passwordConfirm" type="password" placeholder="비밀번호 재입력" />
            <small v-if="errors.passwordConfirm" class="error">{{ errors.passwordConfirm }}</small>
          </label>
        </div>
      </section>

      <section class="section">
        <h2>{{ roleTitle }} 추가 정보</h2>

        <!-- role_code 조건부 렌더링 -->
        <GenderSelect v-if="signupStore.role_code === 0" />

        <template v-else-if="signupStore.role_code === 1">
          <RelationshipSelect />
          <SubjectLinkInput />
        </template>

        <DoctorFields v-else-if="signupStore.role_code === 2" />

        <small v-if="errors.gender" class="error">{{ errors.gender }}</small>
        <small v-if="errors.relationship" class="error">{{ errors.relationship }}</small>
        <small v-if="errors.subject_link_code" class="error">{{ errors.subject_link_code }}</small>
        <small v-if="errors.department" class="error">{{ errors.department }}</small>
        <small v-if="errors.license_number" class="error">{{ errors.license_number }}</small>
        <small v-if="errors.hospital" class="error">{{ errors.hospital }}</small>
        <small v-if="errors.hospital_number" class="error">{{ errors.hospital_number }}</small>
      </section>

      <div class="button-row">
        <button type="button" class="secondary back-icon" @click="goBack" aria-label="이전">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z" fill="currentColor" />
          </svg>
        </button>
        <button type="button" class="primary" :disabled="!isNextEnabled" @click="goNext">다음</button>
      </div>
    </section>
  </main>
</template>

<style scoped>
.signup-page {
  min-height: 100dvh;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 18px 12px 24px;
  background: #eef3f7;
}

.signup-card {
  width: min(820px, 100%);
  background: #ffffff;
  border-radius: 18px;
  padding: 22px;
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.08);
  display: grid;
  gap: 14px;
}

.step-label {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: #2563eb;
}

h1 {
  margin: 0;
  font-size: 30px;
  line-height: 1.3;
  color: #0f172a;
}

.description {
  margin: 0;
  color: #334155;
  font-size: 17px;
  line-height: 1.45;
}

.section {
  border: 1px solid #dde4ec;
  border-radius: 14px;
  padding: 14px;
  display: grid;
  gap: 12px;
}

h2 {
  margin: 0;
  font-size: 21px;
  color: #1e293b;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.field {
  display: grid;
  gap: 8px;
}

.field > span {
  font-size: 17px;
  font-weight: 700;
  color: #1f2937;
}

input {
  width: 100%;
  min-height: 48px;
  border: 1px solid #cfd8df;
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 16px;
}

.error {
  color: #b91c1c;
  font-size: 14px;
  font-weight: 600;
}

.button-row {
  margin-top: 2px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

button {
  min-height: 46px;
  min-width: 96px;
  border: none;
  border-radius: 10px;
  font-size: 17px;
  font-weight: 700;
}

.secondary {
  background: #e2e8f0;
  color: #1e293b;
}

.back-icon {
  min-width: 46px;
  width: 46px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.back-icon svg {
  width: 24px;
  height: 24px;
}

.primary {
  background: #2563eb;
  color: #ffffff;
}

.primary:disabled {
  background: #9cb7f0;
}

@media (max-width: 720px) {
  .field-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
