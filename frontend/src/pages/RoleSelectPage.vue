<script setup lang="ts">
import { useRouter } from "vue-router";

const router = useRouter();

const goBack = () => {
  if (window.history.length > 1) {
    router.back();
    return;
  }

  router.push({ name: "landing" });
};

const selectRole = (role: string) => {
  router.push({ path: "/login", query: { role } });
};
</script>

<template>
  <div class="role-page">
    <div class="role-container">
      <header class="role-header">
        <div class="header-top">
          <button type="button" class="back-button" @click="goBack" aria-label="뒤로 가기">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z" fill="currentColor" />
            </svg>
          </button>
        </div>

        <span class="badge">시니어 헬스케어 음성 AI</span>
        <h1>사용자 유형을 선택해 주세요</h1>
        <p>
          한 번만 선택하면 바로 시작할 수 있습니다.
          큰 글씨와 넓은 버튼으로 편하게 선택하세요.
        </p>
      </header>

      <section class="role-list" aria-label="역할 선택">
        <button class="role-card" @click="selectRole('subject')" aria-label="대상자 선택">
          <div class="pictogram pictogram-subject" aria-hidden="true">
            <svg viewBox="0 0 120 120">
              <circle class="wave-ring ring-1" cx="60" cy="60" r="16" />
              <circle class="wave-ring ring-2" cx="60" cy="60" r="26" />
              <circle class="wave-ring ring-3" cx="60" cy="60" r="36" />
              <rect class="mic-body" x="54" y="42" width="12" height="30" rx="6" />
              <rect class="mic-base" x="48" y="74" width="24" height="8" rx="4" />
              <path class="mic-stand" d="M60 82v10" />
            </svg>
          </div>
          <div class="role-info">
            <h2>대상자</h2>
            <p>말하기 검사를 통해 상태를 확인합니다.</p>
          </div>
        </button>

        <button class="role-card" @click="selectRole('caregiver')" aria-label="보호자 선택">
          <div class="pictogram pictogram-caregiver" aria-hidden="true">
            <svg viewBox="0 0 120 120">
              <path class="house" d="M30 60l30-24 30 24v24H30z" />
              <rect class="door" x="54" y="66" width="12" height="18" rx="4" />
              <path class="heart" d="M60 86c-6-5-9-8-9-12a5 5 0 0 1 9-2a5 5 0 0 1 9 2c0 4-3 7-9 12z" />
            </svg>
          </div>
          <div class="role-info">
            <h2>보호자</h2>
            <p>가족의 상태를 함께 모니터링합니다.</p>
          </div>
        </button>

        <button class="role-card" @click="selectRole('doctor')" aria-label="의료진 선택">
          <div class="pictogram pictogram-doctor" aria-hidden="true">
            <svg viewBox="0 0 120 120">
              <path class="doctor-hair" d="M40 38c0-13 9-22 20-22s20 9 20 22v4H40z" />
              <circle class="doctor-head" cx="60" cy="40" r="15" />
              <path class="doctor-shoulder" d="M24 97c9-14 22-21 36-21s27 7 36 21" />
              <path class="doctor-coat" d="M34 98c6-8 15-12 26-12s20 4 26 12" />
              <path class="doctor-collar" d="M50 78l10 12 10-12" />
              <rect class="doctor-tie" x="54.5" y="86" width="11" height="13.5" rx="4.5" />
              <path class="doctor-stetho-line" d="M38 80v12c0 5-4 9-9 9M82 80v12c0 5 4 9 9 9" />
            </svg>
          </div>
          <div class="role-info">
            <h2>의료진</h2>
            <p>분석 결과를 확인하고 상담합니다.</p>
          </div>
        </button>
      </section>
    </div>
  </div>
</template>

<style scoped>
.role-page,
.role-page * {
  box-sizing: border-box;
}

.role-page {
  min-height: 100vh;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f6f7;
  padding: clamp(16px, 2.6vmin, 32px);
  overflow-y: auto;
}

.role-container {
  width: min(720px, 100%);
  max-width: 720px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  gap: clamp(16px, 2.8vmin, 28px);
  color: #2e2e2e;
  animation: fadeDown 0.7s ease both;
}

.role-header {
  display: grid;
  gap: clamp(10px, 2vmin, 14px);
}

.header-top {
  display: flex;
  justify-content: flex-start;
}

.back-button {
  width: 44px;
  height: 44px;
  padding: 0;
  border: 1px solid #d5dde5;
  border-radius: 999px;
  background: #f5f6f7;
  box-shadow: 6px 6px 12px #d1d9e6, -6px -6px 12px #ffffff;
  color: #1f5f5f;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}

.back-button svg {
  width: 24px;
  height: 24px;
}

.back-button:active {
  transform: translateY(1px);
  box-shadow: inset 3px 3px 7px #d1d9e6, inset -3px -3px 7px #ffffff;
}

.badge {
  background: #e6f3f3;
  color: #1f5f5f;
  padding: clamp(6px, 1.2vmin, 8px) clamp(12px, 2.2vmin, 16px);
  border-radius: 999px;
  font-weight: 700;
  font-size: clamp(0.95rem, 0.85rem + 0.5vmin, 1.1rem);
  align-self: start;
}

.role-header h1 {
  font-size: clamp(1.6rem, 1.3rem + 1.2vmin, 2.1rem);
  font-weight: 900;
  line-height: 1.3;
  margin: 0;
}

.role-header p {
  font-size: clamp(1rem, 0.95rem + 0.5vmin, 1.2rem);
  line-height: 1.6;
  margin: 0;
  color: #5f5f5f;
}

.role-list {
  display: flex;
  flex-direction: column;
  gap: clamp(14px, 2.6vmin, 24px);
}

.role-card {
  width: 100%;
  min-height: clamp(96px, 14vmin, 138px);
  display: flex;
  align-items: center;
  gap: clamp(12px, 2.4vmin, 20px);
  padding: clamp(14px, 2.2vmin, 18px) clamp(16px, 2.8vmin, 20px);
  border: 2px solid transparent;
  border-radius: clamp(20px, 3.6vmin, 28px);
  background: #f5f6f7;
  box-shadow: 10px 10px 22px #d1d9e6, -10px -10px 22px #ffffff;
  cursor: pointer;
  text-align: left;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.role-card:active,
.role-card:focus-visible {
  border-color: #4cb7b7;
  box-shadow: 0 0 0 4px rgba(76, 183, 183, 0.18), 14px 14px 28px #d1d9e6, -14px -14px 28px #ffffff;
}

.role-card:hover {
  transform: translateY(-2px);
}

.pictogram {
  width: clamp(64px, 14vmin, 96px);
  height: clamp(64px, 14vmin, 96px);
  border-radius: clamp(18px, 3.2vmin, 26px);
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: inset 6px 6px 12px rgba(209, 217, 230, 0.7), inset -6px -6px 12px #ffffff;
  flex-shrink: 0;
}

.pictogram svg {
  width: 70%;
  height: 70%;
}

.role-info h2 {
  font-size: clamp(1.2rem, 1.05rem + 0.7vmin, 1.5rem);
  font-weight: 900;
  margin: 0 0 6px;
  color: #2e2e2e;
}

.role-info p {
  font-size: clamp(0.95rem, 0.9rem + 0.5vmin, 1.1rem);
  line-height: 1.6;
  margin: 0;
  color: #5f5f5f;
}

@media (max-width: 480px) {
  .role-page {
    align-items: flex-start;
  }
}

.pictogram-subject .wave-ring {
  fill: none;
  stroke: rgba(76, 183, 183, 0.55);
  stroke-width: 3;
  transform-origin: center;
  animation: wavePulse 3.2s ease-out infinite;
}

.pictogram-subject .ring-2 {
  animation-delay: 1s;
}

.pictogram-subject .ring-3 {
  animation-delay: 2s;
}

.pictogram-subject .mic-body {
  fill: #4cb7b7;
}

.pictogram-subject .mic-base {
  fill: #1f5f5f;
  opacity: 0.85;
}

.pictogram-subject .mic-stand {
  stroke: #1f5f5f;
  stroke-width: 3;
  stroke-linecap: round;
}

.pictogram-caregiver .house {
  fill: none;
  stroke: #4cb7b7;
  stroke-width: 3;
  stroke-linejoin: round;
}

.pictogram-caregiver .door {
  fill: rgba(76, 183, 183, 0.35);
}

.pictogram-caregiver .heart {
  fill: #ff8a80;
  transform-origin: center;
  animation: heartPulse 2.4s ease-in-out infinite;
}

.pictogram-doctor .doctor-hair {
  fill: #2f9f9f;
}

.pictogram-doctor .doctor-head {
  fill: #dff5f5;
}

.pictogram-doctor .doctor-shoulder {
  fill: none;
  stroke: #2f9f9f;
  stroke-width: 8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.pictogram-doctor .doctor-coat {
  fill: none;
  stroke: #4cb7b7;
  stroke-width: 6;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.pictogram-doctor .doctor-collar {
  fill: none;
  stroke: #2f9f9f;
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.pictogram-doctor .doctor-tie {
  fill: #2f9f9f;
}

.pictogram-doctor .doctor-stetho-line {
  fill: none;
  stroke: #4cb7b7;
  stroke-width: 3;
  stroke-linecap: round;
}

@keyframes fadeDown {
  0% { opacity: 0; transform: translateY(-12px); }
  100% { opacity: 1; transform: translateY(0); }
}

@keyframes wavePulse {
  0% { transform: scale(0.7); opacity: 0.7; }
  70% { opacity: 0; }
  100% { transform: scale(1.35); opacity: 0; }
}

@keyframes heartPulse {
  0%, 100% { transform: scale(1); opacity: 0.7; }
  50% { transform: scale(1.2); opacity: 1; }
}

@media (prefers-reduced-motion: reduce) {
  .role-container,
  .pictogram * {
    animation: none !important;
    transition: none !important;
  }
}
</style>
