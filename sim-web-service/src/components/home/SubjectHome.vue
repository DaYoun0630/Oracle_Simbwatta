<script setup lang="ts">
import { computed } from "vue";
import SubjectShell from "@/components/shells/SubjectShell.vue";
import VoiceOrb from "@/components/VoiceOrb.vue";
import { useVoiceSession } from "@/composables/useVoiceSession";

const {
  state,
  isSessionActive,
  startListening,
  voiceLevel,
  isVoiceActive,
  currentTranscript,
  currentResponse,
} = useVoiceSession();

const showIdleLanding = computed(
  () => !isSessionActive.value && state.value === "idle"
);

const statusText = computed(() => {
  switch (state.value) {
    case "listening":
      return "AI 듣는 중";
    case "processing":
      return "AI 생각 중";
    case "speaking":
      return "AI 말하는 중";
    case "cooldown":
      return "곧 말하기 가능";
    default:
      return isSessionActive.value ? "대화 준비 중" : "대화 대기 중";
  }
});

const mainText = computed(() => {
  if (!isSessionActive.value && state.value === "idle") {
    return "안녕하세요!";
  }
  if (state.value === "speaking" && currentResponse.value) {
    return currentResponse.value;
  }
  if (state.value === "listening") {
    return "지금 편하게 말씀해 주세요.";
  }
  if (state.value === "processing") {
    return "답변을 준비하고 있어요.";
  }
  if (state.value === "cooldown") {
    return "답변이 곧 끝나요.";
  }
  return "대화를 이어가 볼게요.";
});

const guidanceText = computed(() => {
  if (!isSessionActive.value && state.value === "idle") {
    return "아래 마이크 버튼을 눌러 시작해 주세요.";
  }
  if (state.value === "listening") {
    return "천천히 또박또박 말씀해 주시면 더 정확하게 인식해요.";
  }
  if (state.value === "processing") {
    return "잠시만 기다려 주세요. AI가 응답을 만들고 있어요.";
  }
  if (state.value === "speaking") {
    return "안내가 끝난 뒤 약 1초 후에 말씀해 주세요.";
  }
  if (state.value === "cooldown") {
    return "지금은 전환 중이에요. 곧 마이크가 자동으로 켜져요.";
  }
  return "원하시는 이야기를 편하게 들려주세요.";
});

const liveCaption = computed(() => {
  if (state.value === "listening" && currentTranscript.value) {
    return `내 말: ${currentTranscript.value}`;
  }
  return "";
});

const statusConfig = computed(() => {
  switch (state.value) {
    case "listening":
      return {
        bgColor: "#eef4f4",
      };
    case "processing":
      return {
        bgColor: "#f0f2f5",
      };
    case "speaking":
      return {
        bgColor: "#f5f6f7",
      };
    case "cooldown":
      return {
        bgColor: "#f5f6f7",
      };
    default:
      return {
        bgColor: "#f5f6f7",
      };
  }
});
</script>

<template>
  <SubjectShell :showHomeButton="isSessionActive" :showMenuButton="true">
    <div class="chat-wrapper" :style="{ backgroundColor: statusConfig.bgColor }">
      <div class="status-area" aria-live="polite">
        <p class="status-chip">{{ statusText }}</p>
        <h1 class="status-text">{{ mainText }}</h1>
        <p class="sub-text">{{ guidanceText }}</p>
        <p v-if="liveCaption" class="live-caption">{{ liveCaption }}</p>
      </div>

      <div class="orb-area">
        <div v-if="showIdleLanding" class="idle-button" @click="startListening">
          <div class="mic-circle">
            <svg width="56" height="56" viewBox="0 0 24 24" fill="white">
              <path
                d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"
              />
              <path
                d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"
              />
            </svg>
          </div>
        </div>

        <div v-else class="orb-container">
          <VoiceOrb :state="state" :size="258" :level="voiceLevel" :reactive="isVoiceActive" />
        </div>
      </div>

      <div class="footer-area">
        <div v-if="isSessionActive" class="status-indicator">
          <span class="pulse-dot"></span>
          <span class="indicator-text">대화 진행 중</span>
        </div>
      </div>
    </div>
  </SubjectShell>
</template>

<style scoped>
.chat-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
  flex: 1;
  min-height: 0;
  padding: 24px 20px 60px;
  transition: background-color 0.5s ease;
}

.status-area {
  text-align: center;
  min-height: 170px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 10px;
}

.status-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  margin: 0 auto;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(76, 183, 183, 0.16);
  color: #1f6b6b;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.2px;
}

.status-text {
  font-size: 1.9rem;
  font-weight: 900;
  color: #2e2e2e;
  margin: 0;
  line-height: 1.4;
}

.sub-text {
  font-size: 1.02rem;
  font-weight: 700;
  color: #3f7272;
  margin: 0;
}

.live-caption {
  margin: 0;
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.72);
  color: #2e2e2e;
  font-size: 0.95rem;
  font-weight: 600;
  line-height: 1.45;
}

.orb-area {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
}

.idle-button {
  cursor: pointer;
  transition: transform 0.2s;
}

.idle-button:active {
  transform: scale(0.95);
}

.mic-circle {
  width: 180px;
  height: 180px;
  background: #4cb7b7;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 20px 40px rgba(76, 183, 183, 0.4);
  animation: gentle-pulse 3s ease-in-out infinite;
}

@keyframes gentle-pulse {
  0%,
  100% {
    transform: scale(1);
    box-shadow: 0 20px 40px rgba(76, 183, 183, 0.4);
  }
  50% {
    transform: scale(1.05);
    box-shadow: 0 25px 50px rgba(76, 183, 183, 0.5);
  }
}

.orb-container {
  display: flex;
  align-items: center;
  justify-content: center;
}

.footer-area {
  min-height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
}

.indicator-text {
  color: #4f5c5c;
  font-size: 0.92rem;
  font-weight: 700;
}

.pulse-dot {
  width: 12px;
  height: 12px;
  background: #4cb7b7;
  border-radius: 50%;
  animation: indicator-pulse 1.2s ease-in-out infinite;
}

@keyframes indicator-pulse {
  0%,
  100% {
    transform: scale(1);
    opacity: 0.75;
  }
  50% {
    transform: scale(1.35);
    opacity: 1;
  }
}
</style>
