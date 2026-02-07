<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

const selectRole = (role: string) => {
  router.push({ path: "/login", query: { role } });
};
</script>

<template>
  <div class="role-page">
    <div class="role-container">
      <header class="role-header">
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
              <rect class="chart" x="30" y="32" width="60" height="56" rx="10" />
              <path class="chart-line" d="M40 70l14-12 14 8 14-16" />
              <circle class="chart-dot" cx="82" cy="50" r="4" />
              <path class="stethoscope" d="M46 42v12c0 8 6 14 14 14s14-6 14-14V42" />
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

.pictogram-doctor .chart {
  fill: none;
  stroke: #4cb7b7;
  stroke-width: 3;
}

.pictogram-doctor .chart-line {
  fill: none;
  stroke: #4cb7b7;
  stroke-width: 3;
  stroke-linecap: round;
  stroke-dasharray: 48;
  stroke-dashoffset: 48;
  animation: lineFlow 3.2s ease-in-out infinite;
}

.pictogram-doctor .chart-dot {
  fill: #1f5f5f;
  animation: dotPulse 2.2s ease-in-out infinite;
}

.pictogram-doctor .stethoscope {
  fill: none;
  stroke: rgba(76, 183, 183, 0.5);
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

@keyframes lineFlow {
  0% { stroke-dashoffset: 48; opacity: 0.3; }
  50% { opacity: 1; }
  100% { stroke-dashoffset: 0; opacity: 0.4; }
}

@keyframes dotPulse {
  0%, 100% { transform: scale(1); opacity: 0.6; }
  50% { transform: scale(1.3); opacity: 1; }
}

@media (prefers-reduced-motion: reduce) {
  .role-container,
  .pictogram * {
    animation: none !important;
    transition: none !important;
  }
}
</style>
