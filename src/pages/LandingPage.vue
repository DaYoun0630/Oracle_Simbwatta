<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const authStore = useAuthStore();

const slides = [
  {
    id: "voice",
    title: "정밀 분석",
    subtitle: "음성 변화를 빠르게 포착",
    description: "소리 파형을 정밀하게 스캔하여 작은 변화도 놓치지 않습니다."
  },
  {
    id: "ai",
    title: "인지 판별",
    subtitle: "AI 기반 신뢰도 제시",
    description: "데이터 포인트가 연결되며 결과를 명확하게 보여줍니다."
  },
  {
    id: "monitor",
    title: "안심 알림",
    subtitle: "보호자와 실시간 공유",
    description: "중요한 변화를 부드러운 알림으로 빠르게 전달합니다."
  }
];

const currentIndex = ref(0);
const isOffline = ref(!navigator.onLine);

const slideTrackStyle = computed(() => ({
  transform: `translateX(-${currentIndex.value * 100}%)`
}));

let slideTimer: ReturnType<typeof setInterval> | null = null;

const startAutoSlide = () => {
  slideTimer = window.setInterval(() => {
    currentIndex.value = (currentIndex.value + 1) % slides.length;
  }, 5000);
};

const stopAutoSlide = () => {
  if (slideTimer) {
    window.clearInterval(slideTimer);
    slideTimer = null;
  }
};

const startService = () => {
  if (isOffline.value) {
    window.alert("네트워크 연결을 확인한 뒤 다시 시도해주세요.");
    return;
  }

  // 기존 세션을 초기화하고 역할 선택으로 이동
  authStore.clear();
  router.push({ name: "select-role" }).catch((error) => {
    console.error("Failed to navigate to role selection:", error);
    window.location.assign("/select-role");
  });
};

const syncNetworkState = () => {
  isOffline.value = !navigator.onLine;
};

onMounted(() => {
  startAutoSlide();
  window.addEventListener("online", syncNetworkState);
  window.addEventListener("offline", syncNetworkState);
});

onUnmounted(() => {
  stopAutoSlide();
  window.removeEventListener("online", syncNetworkState);
  window.removeEventListener("offline", syncNetworkState);
});
</script>

<template>
  <div class="landing-viewport">
    <div class="landing">
      <header class="hero">
        <span class="service-badge">시니어 헬스케어 음성 AI</span>
        <h1>
          말 한마디로 지키는<br />
          <strong>인지 건강 모니터링</strong>
        </h1>
        <p>
          복잡한 절차 없이 쉽게 시작하고,<br />
          큰 글씨와 선명한 화면으로<br />
          누구나 편하게 사용할 수 있습니다.
        </p>
      </header>

      <section class="carousel" aria-label="서비스 기능 소개">
        <div class="carousel-window">
          <div class="slides" :style="slideTrackStyle">
            <article v-for="slide in slides" :key="slide.id" class="slide">
              <div class="slide-card">
                <div class="pictogram" :class="`pictogram-${slide.id}`">
                  <svg v-if="slide.id === 'voice'" viewBox="0 0 140 140" aria-hidden="true">
                    <circle class="pg-ring ring-1" cx="70" cy="70" r="20" />
                    <circle class="pg-ring ring-2" cx="70" cy="70" r="32" />
                    <circle class="pg-ring ring-3" cx="70" cy="70" r="44" />
                    <path class="pg-wave" d="M24 70c10-12 20-12 30 0s20 12 30 0 20-12 30 0" />
                    <rect class="pg-scan" x="28" y="56" width="84" height="6" rx="3" />
                    <rect class="pg-mic" x="64" y="50" width="12" height="30" rx="6" />
                    <rect class="pg-mic-base" x="56" y="82" width="28" height="8" rx="4" />
                  </svg>

                  <svg v-else-if="slide.id === 'ai'" viewBox="0 0 140 140" aria-hidden="true">
                    <circle class="pg-head" cx="70" cy="58" r="26" />
                    <rect class="pg-neck" x="60" y="84" width="20" height="16" rx="8" />
                    <circle class="pg-node" cx="58" cy="52" r="4" />
                    <circle class="pg-node" cx="78" cy="46" r="4" />
                    <circle class="pg-node" cx="84" cy="68" r="4" />
                    <circle class="pg-node" cx="60" cy="72" r="4" />
                    <line class="pg-link" x1="58" y1="52" x2="78" y2="46" />
                    <line class="pg-link" x1="78" y1="46" x2="84" y2="68" />
                    <line class="pg-link" x1="84" y1="68" x2="60" y2="72" />
                    <circle class="pg-badge" cx="96" cy="88" r="14" />
                    <path class="pg-check" d="M90 88l4 4 8-8" />
                  </svg>

                  <svg v-else viewBox="0 0 140 140" aria-hidden="true">
                    <circle class="pg-person" cx="40" cy="56" r="12" />
                    <rect class="pg-body" x="30" y="70" width="20" height="20" rx="8" />
                    <circle class="pg-person" cx="100" cy="56" r="12" />
                    <rect class="pg-body" x="90" y="70" width="20" height="20" rx="8" />
                    <path class="pg-signal" d="M52 62c12-14 24-14 36 0" />
                    <path class="pg-signal" d="M52 74c12-14 24-14 36 0" />
                    <path class="pg-signal" d="M52 86c12-14 24-14 36 0" />
                    <path class="pg-heart" d="M70 100c-8-6-12-10-12-16a6 6 0 0 1 12-3a6 6 0 0 1 12 3c0 6-4 10-12 16z" />
                  </svg>
                </div>

                <h3 class="slide-title">
                  <span class="highlight">{{ slide.title }}</span>
                  <span class="subtitle">{{ slide.subtitle }}</span>
                </h3>
                <p class="slide-desc">{{ slide.description }}</p>
              </div>
            </article>
          </div>
        </div>
      </section>

      <div class="footer">
        <div class="indicator" role="presentation">
          <span
            v-for="(_, index) in slides"
            :key="index"
            class="dot"
            :class="{ active: index === currentIndex }"
          ></span>
        </div>

        <button class="cta-button" :disabled="isOffline" @click="startService">
          {{ isOffline ? "네트워크 연결 필요" : "서비스 시작하기" }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.landing-viewport,
.landing-viewport * {
  box-sizing: border-box;
}

.landing-viewport {
  width: 100%;
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f6f7;
  padding: clamp(12px, 2.6vmin, 32px);
  overflow-y: auto;
}

.landing {
  width: min(100%, 860px);
  min-height: min(calc(100dvh - clamp(24px, 5vmin, 64px)), 844px);
  background: transparent;
  padding: clamp(16px, 3vmin, 28px);
  display: grid;
  grid-template-rows:
    auto
    1fr
    auto;
  gap: clamp(12px, 2.5vmin, 20px);
  color: #2e2e2e;
}

.hero {
  display: grid;
  gap: clamp(8px, 2vmin, 12px);
  padding-inline: 4px;
}

.service-badge {
  background: #e6f3f3;
  color: #1f5f5f;
  padding: clamp(6px, 1.2vmin, 8px) clamp(12px, 2.2vmin, 16px);
  border-radius: 999px;
  font-weight: 700;
  font-size: clamp(0.9rem, 0.85rem + 0.5vmin, 1.05rem);
  align-self: start;
}

.hero h1 {
  font-size: clamp(1.5rem, 1.2rem + 1.4vmin, 2rem);
  font-weight: 900;
  line-height: 1.3;
  margin: 0;
}

.hero h1 strong {
  color: #4cb7b7;
  font-weight: 900;
}

.hero p {
  font-size: clamp(0.95rem, 0.9rem + 0.5vmin, 1.05rem);
  line-height: 1.5;
  margin: 0;
  color: #5f5f5f;
}

.carousel {
  flex: 1;
  background: #f0f3f4;
  border-radius: clamp(18px, 3.6vmin, 28px);
  box-shadow: inset 6px 6px 14px rgba(209, 217, 230, 0.7), inset -6px -6px 14px #ffffff;
  display: flex;
  min-height: clamp(260px, 36vmin, 420px);
  padding: clamp(8px, 1.6vmin, 14px);
}

.carousel-window {
  width: 100%;
  overflow: hidden;
}

.slides {
  display: flex;
  height: 100%;
  transition: transform 0.7s ease;
}

.slide {
  min-width: 100%;
  height: 100%;
  display: flex;
  padding: clamp(6px, 1.4vmin, 10px);
}

.slide-card {
  flex: 1;
  background: #ffffff;
  border-radius: clamp(18px, 3.6vmin, 26px);
  box-shadow: 10px 10px 20px #d1d9e6, -10px -10px 20px #ffffff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: clamp(8px, 1.6vmin, 12px);
  text-align: center;
  padding: clamp(12px, 2.4vmin, 18px) clamp(16px, 3vmin, 24px);
}

.pictogram {
  width: clamp(92px, 22vmin, 156px);
  height: clamp(92px, 22vmin, 156px);
  border-radius: clamp(18px, 3.6vmin, 26px);
  background: #f5f6f7;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: inset 6px 6px 12px rgba(209, 217, 230, 0.7), inset -6px -6px 12px #ffffff;
}

.pictogram svg {
  width: 80%;
  height: 80%;
}

.slide-title {
  font-size: clamp(1.2rem, 1.05rem + 0.8vmin, 1.5rem);
  font-weight: 800;
  line-height: 1.3;
  margin: 0;
}

.slide-title .highlight {
  display: block;
  color: #4cb7b7;
  font-weight: 900;
  font-size: clamp(1.35rem, 1.1rem + 1vmin, 1.7rem);
}

.slide-title .subtitle {
  display: block;
  font-size: clamp(1rem, 0.95rem + 0.6vmin, 1.15rem);
  font-weight: 700;
}

.slide-desc {
  font-size: clamp(0.9rem, 0.85rem + 0.5vmin, 1.05rem);
  line-height: 1.5;
  color: #5f5f5f;
  margin: 0;
}

.footer {
  display: grid;
  gap: clamp(8px, 1.6vmin, 12px);
  padding-top: clamp(6px, 1.4vmin, 10px);
}

.indicator {
  display: flex;
  justify-content: center;
  gap: clamp(8px, 2.2vmin, 12px);
}

.dot {
  width: clamp(10px, 2.6vmin, 16px);
  height: clamp(10px, 2.6vmin, 16px);
  background: #c9d6d6;
  border-radius: 999px;
  transition: all 0.3s ease;
}

.dot.active {
  width: clamp(22px, 5vmin, 32px);
  background: #4cb7b7;
  box-shadow: 0 0 12px rgba(76, 183, 183, 0.45);
}

.cta-button {
  height: clamp(48px, 6.5vmin, 60px);
  border: none;
  border-radius: clamp(16px, 3vmin, 22px);
  background: #4cb7b7;
  color: #ffffff;
  font-size: clamp(1rem, 0.95rem + 0.5vmin, 1.1rem);
  font-weight: 900;
  box-shadow: 0 12px 22px rgba(76, 183, 183, 0.35);
  cursor: pointer;
}

.cta-button:active {
  transform: translateY(1px);
  box-shadow: 0 8px 16px rgba(76, 183, 183, 0.25);
}

.cta-button:disabled {
  background: #9fbcbc;
  box-shadow: none;
  cursor: not-allowed;
}

.pictogram-voice .pg-ring {
  fill: none;
  stroke: rgba(76, 183, 183, 0.45);
  stroke-width: 3;
  transform-origin: center;
  animation: wavePulse 3.6s ease-out infinite;
}

.pictogram-voice .ring-2 {
  animation-delay: 1s;
}

.pictogram-voice .ring-3 {
  animation-delay: 2s;
}

.pictogram-voice .pg-wave {
  fill: none;
  stroke: #4cb7b7;
  stroke-width: 3.2;
  stroke-linecap: round;
}

.pictogram-voice .pg-scan {
  fill: rgba(76, 183, 183, 0.3);
  animation: scanMove 2.8s ease-in-out infinite;
}

.pictogram-voice .pg-mic {
  fill: #4cb7b7;
}

.pictogram-voice .pg-mic-base {
  fill: #1f5f5f;
  opacity: 0.85;
}

.pictogram-ai .pg-head {
  fill: none;
  stroke: #4cb7b7;
  stroke-width: 3.2;
}

.pictogram-ai .pg-neck {
  fill: rgba(76, 183, 183, 0.8);
}

.pictogram-ai .pg-node {
  fill: #1f5f5f;
  animation: nodePulse 2.6s ease-in-out infinite;
}

.pictogram-ai .pg-link {
  stroke: #4cb7b7;
  stroke-width: 2.4;
  stroke-dasharray: 40;
  stroke-dashoffset: 40;
  animation: linkDraw 3.2s ease-in-out infinite;
}

.pictogram-ai .pg-badge {
  fill: rgba(76, 183, 183, 0.2);
  stroke: #4cb7b7;
  stroke-width: 2.4;
  animation: badgeGlow 2.8s ease-in-out infinite;
}

.pictogram-ai .pg-check {
  fill: none;
  stroke: #1f5f5f;
  stroke-width: 3.2;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: 22;
  stroke-dashoffset: 22;
  animation: checkDraw 3.2s ease-in-out infinite;
}

.pictogram-monitor .pg-person {
  fill: #4cb7b7;
}

.pictogram-monitor .pg-body {
  fill: rgba(76, 183, 183, 0.8);
}

.pictogram-monitor .pg-signal {
  fill: none;
  stroke: #1f5f5f;
  stroke-width: 2.6;
  stroke-linecap: round;
  stroke-dasharray: 36;
  stroke-dashoffset: 36;
  animation: linkDraw 3s ease-in-out infinite;
}

.pictogram-monitor .pg-heart {
  fill: #ff8a80;
  transform-origin: center;
  animation: heartPulse 2.4s ease-in-out infinite;
}

@keyframes wavePulse {
  0% { transform: scale(0.7); opacity: 0.7; }
  70% { opacity: 0; }
  100% { transform: scale(1.3); opacity: 0; }
}

@keyframes scanMove {
  0% { transform: translateY(-10px); opacity: 0; }
  40% { opacity: 1; }
  60% { opacity: 1; }
  100% { transform: translateY(16px); opacity: 0; }
}

@keyframes nodePulse {
  0%, 100% { transform: scale(1); opacity: 0.7; }
  50% { transform: scale(1.2); opacity: 1; }
}

@keyframes linkDraw {
  0% { stroke-dashoffset: 40; opacity: 0.3; }
  50% { opacity: 1; }
  100% { stroke-dashoffset: 0; opacity: 0.4; }
}

@keyframes checkDraw {
  0% { stroke-dashoffset: 22; opacity: 0; }
  50% { opacity: 1; }
  100% { stroke-dashoffset: 0; opacity: 1; }
}

@keyframes badgeGlow {
  0%, 100% { transform: scale(1); opacity: 0.6; }
  50% { transform: scale(1.1); opacity: 1; }
}

@keyframes heartPulse {
  0%, 100% { transform: scale(1); opacity: 0.7; }
  50% { transform: scale(1.2); opacity: 1; }
}

@media (max-width: 480px) {
  .landing-viewport {
    align-items: flex-start;
    padding-top: 12px;
    padding-bottom: calc(12px + env(safe-area-inset-bottom));
    padding-left: max(12px, env(safe-area-inset-left));
    padding-right: max(12px, env(safe-area-inset-right));
  }

  .landing {
    width: min(100%, 390px);
    min-height: min(calc(100dvh - 24px), 844px);
    padding: 16px 14px 18px;
    gap: 12px;
  }

  .hero {
    padding-inline: 8px;
  }

  .carousel {
    min-height: clamp(320px, 44vh, 420px);
  }
}

@media (min-width: 1024px) {
  .landing {
    width: min(100%, 1120px);
    min-height: min(calc(100dvh - 64px), 860px);
    grid-template-columns: minmax(320px, 1fr) minmax(380px, 1.15fr);
    grid-template-rows: 1fr auto;
    grid-template-areas:
      "hero carousel"
      "footer footer";
    column-gap: clamp(24px, 4vw, 52px);
    row-gap: clamp(14px, 2.2vh, 24px);
    align-items: stretch;
  }

  .hero {
    grid-area: hero;
    align-content: center;
  }

  .carousel {
    grid-area: carousel;
    min-height: 0;
  }

  .footer {
    grid-area: footer;
    width: min(100%, 560px);
    margin: 0 auto;
  }
}
</style>
