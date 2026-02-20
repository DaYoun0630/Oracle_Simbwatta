<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { useSignupStore } from "@/stores/signup";

const router = useRouter();
const signupStore = useSignupStore();

const roleToLoginQuery: Record<number, string> = {
  0: "subject",
  1: "caregiver",
  2: "doctor",
};

const loginRole = computed(() => {
  if (signupStore.role_code === null) return "subject";
  return roleToLoginQuery[signupStore.role_code];
});

const goLoginPage = () => {
  const queryRole = loginRole.value;
  signupStore.reset();
  router.push({
    name: "login",
    query: { role: queryRole },
  });
};
</script>

<template>
  <main class="signup-page">
    <section class="signup-card">
      <p class="step-label">회원가입 4 / 4</p>
      <h1>회원가입이 완료되었습니다</h1>
      <p class="description">
        로그인 후 서비스를 바로 이용할 수 있습니다. 필요 시 정보는 설정 화면에서 수정할 수 있습니다.
      </p>

      <div class="summary-box">
        <p><strong>가입 역할:</strong> {{ signupStore.roleLabel }}</p>
        <p><strong>이메일:</strong> {{ signupStore.email || "-" }}</p>
        <p><strong>회원 번호:</strong> {{ signupStore.lastSignupUserId || "발급 완료" }}</p>
      </div>

      <button type="button" class="primary" @click="goLoginPage">로그인 페이지로 이동</button>
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
  width: min(640px, 100%);
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

.summary-box {
  border: 1px solid #d9e1e8;
  border-radius: 14px;
  padding: 14px;
  display: grid;
  gap: 8px;
  background: #f8fafc;
}

.summary-box p {
  margin: 0;
  font-size: 17px;
  color: #1e293b;
}

.primary {
  min-height: 48px;
  border: none;
  border-radius: 10px;
  font-size: 18px;
  font-weight: 700;
  color: #ffffff;
  background: #2563eb;
}
</style>
