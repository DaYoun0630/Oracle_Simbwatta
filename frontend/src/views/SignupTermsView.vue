<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useSignupStore } from "@/stores/signup";

const router = useRouter();
const signupStore = useSignupStore();

const agreeService = ref(false);
const agreePrivacy = ref(false);
const agreeMarketing = ref(false);
const agreeHealthHighwayLink = ref(false);
const agreeHealthSensitive = ref(false);
const agreeHealthTransfer = ref(false);
const submitError = ref("");

const canSubmit = computed(
  () => agreeService.value && agreePrivacy.value && !signupStore.isSubmitting
);

const goBack = () => {
  router.push({ name: "signup-form" });
};

const noop = () => {};

const submitSignup = async () => {
  submitError.value = "";

  if (!agreeService.value || !agreePrivacy.value) {
    submitError.value = "필수 약관에 동의해 주세요.";
    return;
  }

  try {
    await signupStore.submitSignup({
      agree_service: agreeService.value,
      agree_privacy: agreePrivacy.value,
      agree_marketing: agreeMarketing.value,
    });

    router.push({ name: "signup-complete" });
  } catch (error) {
    console.error("Signup failed:", error);
    submitError.value = "회원가입 처리 중 오류가 발생했습니다. 다시 시도해 주세요.";
  }
};

onMounted(() => {
  if (signupStore.role_code === null) {
    router.replace({ name: "signup-role" });
    return;
  }

  if (!signupStore.canProceedToTerms) {
    router.replace({ name: "signup-form" });
  }
});
</script>

<template>
  <main class="signup-page">
    <section class="signup-card">
      <p class="step-label">회원가입 3 / 4</p>
      <h1>이용약관 동의</h1>
      <p class="description">필수 약관에 동의하면 회원가입을 완료할 수 있습니다.</p>

      <section class="terms-box">
        <label class="check-row required">
          <input v-model="agreeService" type="checkbox" />
          <span>[필수] 서비스 이용약관 동의</span>
        </label>
        <p class="term-content">
          서비스 제공을 위해 필요한 기본 이용 정책에 동의합니다. 회원 계정 및 서비스 이용 이력을
          관리합니다.
        </p>

        <label class="check-row required">
          <input v-model="agreePrivacy" type="checkbox" />
          <span>[필수] 개인정보 수집 및 이용 동의</span>
        </label>
        <p class="term-content">
          회원가입과 건강 관리 서비스 제공을 위해 최소한의 개인정보를 수집/이용합니다.
        </p>

        <label class="check-row">
          <input v-model="agreeMarketing" type="checkbox" />
          <span>[선택] 혜택 및 공지 알림 수신 동의</span>
        </label>

        <div class="agreement-group">
          <p class="agreement-title">건강정보 고속도로 연동</p>
          <p class="agreement-description">
            연동 시 진료·투약·검사 등 건강정보를 불러와 맞춤 기능을 제공합니다. 언제든 해지할 수
            있습니다.
          </p>

          <label class="check-row">
            <input v-model="agreeHealthHighwayLink" type="checkbox" />
            <span>[선택] 건강정보 고속도로 연동하기</span>
          </label>
          <p class="term-content">가입 후 바로 연동을 진행합니다.</p>

          <div class="check-row required check-row-split">
            <label class="check-inline">
              <input v-model="agreeHealthSensitive" type="checkbox" />
              <span>[필수] 건강정보(민감정보) 수집·이용 동의</span>
            </label>
            <button type="button" class="detail-link" @click.prevent="noop">자세히</button>
          </div>
          <p class="term-content">건강정보 기반 기능 제공을 위해 필요한 범위 내에서 처리합니다.</p>

          <div class="check-row required check-row-split">
            <label class="check-inline">
              <input v-model="agreeHealthTransfer" type="checkbox" />
              <span>[필수] 건강정보 고속도로를 통한 전송·연계 동의</span>
            </label>
            <button type="button" class="detail-link" @click.prevent="noop">자세히</button>
          </div>
          <p class="term-content">본인 동의로 건강정보 고속도로에서 데이터를 받아옵니다.</p>

          <div class="agreement-actions">
            <button type="button" class="range-button" @click="noop">데이터 범위 선택(추후)</button>
          </div>
        </div>
      </section>

      <p v-if="submitError" class="error">{{ submitError }}</p>

      <div class="button-row">
        <button type="button" class="secondary back-icon" @click="goBack" aria-label="이전">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z" fill="currentColor" />
          </svg>
        </button>
        <button type="button" class="primary" :disabled="!canSubmit" @click="submitSignup">
          {{ signupStore.isSubmitting ? "처리 중..." : "회원가입 완료" }}
        </button>
      </div>
    </section>
  </main>
</template>

<style scoped>
.signup-page {
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px 14px;
  background: #eef3f7;
}

.signup-card {
  width: min(780px, 100%);
  background: #ffffff;
  border-radius: 18px;
  padding: 24px;
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

.terms-box {
  border: 1px solid #d9e1e8;
  border-radius: 14px;
  padding: 14px;
  display: grid;
  gap: 10px;
}

.check-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
}

.check-row.required span {
  color: #0f172a;
}

input[type="checkbox"] {
  width: 20px;
  height: 20px;
  min-width: 20px;
  min-height: 20px;
  flex: 0 0 20px;
}

.term-content {
  margin: 0 0 8px 30px;
  color: #475569;
  font-size: 15px;
  line-height: 1.5;
}

.agreement-group {
  margin-top: 2px;
  padding-top: 14px;
  border-top: 1px solid #e2e8f0;
  display: grid;
  gap: 10px;
}

.agreement-title {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
  color: #0f172a;
}

.agreement-description {
  margin: 0;
  color: #64748b;
  font-size: 14px;
  line-height: 1.5;
}

.check-row-split {
  justify-content: space-between;
  gap: 12px;
}

.check-inline {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.check-inline span {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
}

.detail-link {
  min-height: auto;
  min-width: 0;
  border: none;
  border-radius: 0;
  background: transparent;
  color: #2563eb;
  font-size: 14px;
  font-weight: 700;
  padding: 0;
  line-height: 1;
  cursor: pointer;
}

.detail-link:hover {
  text-decoration: underline;
}

.agreement-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 2px;
}

.range-button {
  min-width: 0;
  min-height: 40px;
  padding: 0 14px;
  font-size: 15px;
  font-weight: 700;
  background: #e2e8f0;
  color: #1e293b;
}

.error {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #b91c1c;
}

.button-row {
  margin-top: 4px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

button {
  min-height: 46px;
  min-width: 110px;
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
</style>
