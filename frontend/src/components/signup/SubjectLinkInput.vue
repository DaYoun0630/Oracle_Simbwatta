<script setup lang="ts">
import { computed } from "vue";
import { useSignupStore } from "@/stores/signup";

const signupStore = useSignupStore();

const canCheckCode = computed(
  () => signupStore.subject_link_code.trim().length > 0 && !signupStore.isCheckingSubjectCode
);

const messageClass = computed(() => {
  if (!signupStore.subjectCodeMessage) return "";
  return signupStore.subjectCodeVerified ? "message success" : "message error";
});

const onCodeInput = () => {
  signupStore.resetSubjectCodeVerification();
};

const checkCode = async () => {
  await signupStore.validateSubjectLinkCode();
};
</script>

<template>
  <div class="field-group">
    <label class="field">
      <span class="field-label">대상자 회원번호</span>
      <input
        v-model="signupStore.subject_link_code"
        type="text"
        name="subject_link_code"
        autocomplete="on"
        placeholder="예: SM-123456"
        @input="onCodeInput"
      />
    </label>

    <button type="button" class="check-button" :disabled="!canCheckCode" @click="checkCode">
      {{ signupStore.isCheckingSubjectCode ? "확인 중..." : "회원번호 확인" }}
    </button>

    <p v-if="signupStore.subjectCodeMessage" :class="messageClass">
      {{ signupStore.subjectCodeMessage }}
    </p>
  </div>
</template>

<style scoped>
.field-group {
  display: grid;
  gap: 10px;
}

.field {
  display: grid;
  gap: 8px;
}

.field-label {
  font-size: 18px;
  font-weight: 700;
}

input {
  width: 100%;
  min-height: 48px;
  border: 1px solid #cfd8df;
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 16px;
}

.check-button {
  min-height: 46px;
  border: none;
  border-radius: 10px;
  font-size: 16px;
  font-weight: 700;
  color: #ffffff;
  background: #2d7fb8;
  cursor: pointer;
}

.check-button:disabled {
  background: #a2b7c8;
  cursor: not-allowed;
}

.message {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.message.success {
  color: #176a3a;
}

.message.error {
  color: #b91c1c;
}
</style>
