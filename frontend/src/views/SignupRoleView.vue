<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { useSignupStore, type RoleCode } from "@/stores/signup";

const router = useRouter();
const signupStore = useSignupStore();

const roleOptions: Array<{ code: RoleCode; title: string; description: string }> = [
  {
    code: 0,
    title: "대상자",
    description: "음성 검사와 건강 관리를 직접 이용하는 사용자",
  },
  {
    code: 1,
    title: "보호자",
    description: "대상자의 상태를 함께 확인하고 돌보는 사용자",
  },
  {
    code: 2,
    title: "의사",
    description: "임상 정보를 확인하고 상담을 진행하는 사용자",
  },
];

const hasSelectedRole = computed(() => signupStore.role_code !== null);

const selectRole = (roleCode: RoleCode) => {
  signupStore.setRole(roleCode);
};

const goNext = () => {
  if (!hasSelectedRole.value) return;
  router.push({ name: "signup-form" });
};

const goBack = () => {
  // 회원가입 진입점으로 돌아갈 때는 선택 상태를 초기화한다.
  signupStore.reset();
  router.push({ name: "landing" });
};
</script>

<template>
  <main class="signup-page">
    <section class="signup-card">
      <p class="step-label">회원가입 1 / 4</p>
      <h1>가입 역할을 선택해 주세요</h1>
      <p class="description">선택한 역할에 맞는 정보만 보여드려서 더 쉽게 입력할 수 있습니다.</p>

      <div class="role-list">
        <button
          v-for="role in roleOptions"
          :key="role.code"
          type="button"
          class="role-item"
          :class="{ selected: signupStore.role_code === role.code }"
          @click="selectRole(role.code)"
        >
          <strong>{{ role.title }}</strong>
          <span>{{ role.description }}</span>
          <small>코드: {{ role.code }}</small>
        </button>
      </div>

      <div class="button-row">
        <button type="button" class="secondary back-icon" @click="goBack" aria-label="이전">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z" fill="currentColor" />
          </svg>
        </button>
        <button type="button" class="primary" :disabled="!hasSelectedRole" @click="goNext">
          다음
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
  width: min(720px, 100%);
  background: #eef3f7;
  border-radius: 18px;
  padding: 24px;
  border: 1px solid #dde5ed;
  box-shadow:
    14px 14px 28px rgba(182, 194, 208, 0.7),
    -14px -14px 28px rgba(255, 255, 255, 0.95),
    inset 1px 1px 0 rgba(255, 255, 255, 0.8),
    inset -1px -1px 0 rgba(194, 205, 218, 0.65);
  display: grid;
  gap: 14px;
}

.step-label {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: #4cb7b7;
}

h1 {
  margin: 0;
  font-size: 30px;
  line-height: 1.3;
  color: #0f172a;
}

.description {
  margin: 0;
  font-size: 18px;
  line-height: 1.45;
  color: #334155;
}

.role-list {
  margin-top: 8px;
  display: grid;
  gap: 10px;
}

.role-item {
  width: 100%;
  text-align: left;
  border: 1px solid #d6dee6;
  border-radius: 12px;
  background: #ffffff;
  padding: 14px;
  display: grid;
  gap: 6px;
  cursor: pointer;
}

.role-item strong {
  font-size: 20px;
}

.role-item span {
  font-size: 16px;
  color: #475569;
}

.role-item small {
  font-size: 13px;
  color: #64748b;
}

.role-item.selected {
  border-color: #4cb7b7;
  background: #e9f7f7;
}

.button-row {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

button {
  min-height: 46px;
  min-width: 96px;
  border: 1px solid #4cb7b7;
  border-radius: 10px;
  font-size: 17px;
  font-weight: 700;
  transition: transform 0.12s ease, box-shadow 0.12s ease, filter 0.12s ease;
}

.secondary {
  background: #4cb7b7;
  color: #ffffff;
  border: 1px solid #4cb7b7;
  box-shadow: 0 6px 14px rgba(76, 183, 183, 0.25);
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
  background: #4cb7b7;
  color: #ffffff;
  box-shadow: 0 8px 16px rgba(76, 183, 183, 0.28);
}

.primary:disabled {
  background: #4cb7b7 !important;
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff;
  opacity: 0.62;
  box-shadow: none;
  cursor: not-allowed;
}

.secondary:active,
.primary:active {
  transform: translateY(2px);
  box-shadow:
    inset 4px 4px 8px rgba(15, 23, 42, 0.15),
    inset -3px -3px 6px rgba(255, 255, 255, 0.7);
  filter: brightness(0.98);
}
</style>
