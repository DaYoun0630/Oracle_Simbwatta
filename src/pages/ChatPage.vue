<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import VoiceOrb from "../components/VoiceOrb.vue";
import { useVoiceSession } from "../composables/useVoiceSession";

// 라우팅 이동을 위한 router 인스턴스
const router = useRouter();

// 음성 대화 세션 상태/메시지/제어 함수 모음
const {
  state,
  messages,
  currentTranscript,
  currentResponse,
  startListening,
  stopListening,
  resetSession,
} = useVoiceSession();

// 시각화 컴포넌트에 전달할 상태(일시정지는 processing으로 치환)
const visualState = computed(() => (state.value === "pause" ? "processing" : state.value));

// 마지막 assistant 발화만 추출(없으면 빈 문자열)
const lastAssistantMessage = computed(() => {
  for (let i = messages.value.length - 1; i >= 0; i -= 1) {
    if (messages.value[i].role === "assistant") {
      return messages.value[i].content;
    }
  }
  return "";
});

// 메인 안내 텍스트(현재 상태에 따라 우선순위 변경)
const mainText = computed(() => {
  if (state.value === "speaking" && currentResponse.value) {
    return currentResponse.value;
  }
  if (state.value === "processing") {
    return "AI가 답변을 준비하고 있어요.";
  }
  if (state.value === "listening") {
    return "말씀을 듣고 있어요.";
  }
  if (lastAssistantMessage.value) {
    return lastAssistantMessage.value;
  }
  return "오늘은 어떤 이야기를 나누고 싶으신가요?";
});

// 보조 안내 문구(상태별 톤/가이드 제공)
const supportiveText = computed(() => {
  if (state.value === "listening") {
    return "말씀을 참 잘하시네요. 천천히 이어서 말씀해 주세요.";
  }
  if (state.value === "processing") {
    return "조금만 기다려 주세요. 생각을 정리하고 있어요.";
  }
  if (state.value === "speaking") {
    return "차분히 알려드릴게요. 편하게 들어주세요.";
  }
  if (lastAssistantMessage.value) {
    return "궁금한 점이 있으면 언제든 말씀해 주세요.";
  }
  return "마이크 버튼을 누르면 대화가 시작됩니다.";
});

// 자막 영역에 보여줄 내 말 텍스트(청취 중에만 표시)
const transcriptText = computed(() => {
  if (state.value === "listening" && currentTranscript.value) {
    return currentTranscript.value;
  }
  if (state.value === "listening") {
    return "말씀을 들으며 내용을 정리하고 있어요.";
  }
  if (state.value === "idle") {
    return "마이크 버튼을 눌러 대화를 시작하세요.";
  }
  return "";
});

// 마이크 버튼 하단 라벨 텍스트
const micLabel = computed(() => {
  if (state.value === "listening") return "듣는 중";
  if (state.value === "processing") return "생각 중";
  if (state.value === "speaking") return "답변 중";
  return "말하기 시작";
});

// 마이크가 청취 중인지 여부
const isListening = computed(() => state.value === "listening");
// 마이크 버튼 비활성 조건(대기/청취 외에는 클릭 불가)
const isMicDisabled = computed(() => !["idle", "listening"].includes(state.value));

// 마이크 버튼 클릭 처리: 대기 → 청취 시작, 청취 → 청취 종료
const handleMicClick = () => {
  if (state.value === "idle") {
    startListening();
    return;
  }
  if (state.value === "listening") {
    stopListening();
  }
};

// 대화 종료: 세션 초기화 후 홈으로 이동
const handleEndConversation = () => {
  resetSession();
  router.push({ name: "home" });
};
</script>

<template>
  <!-- 전체 뷰포트(배경 포함) -->
  <div class="chat-viewport">
    <!-- 중앙 컨테이너 -->
    <div class="chat-container">
      <!-- 상단 헤더 -->
      <header class="chat-top">
        <button class="end-button" type="button" @click="handleEndConversation">
          대화 마치기
        </button>
      </header>

      <!-- 본문(안내 카드 + 오브 + 자막) -->
      <section class="chat-body">
        <!-- AI 안내 카드 -->
        <div class="ai-card" aria-live="polite">
          <span class="ai-label">AI 안내</span>
          <p class="ai-message">{{ mainText }}</p>
          <p class="ai-sub">{{ supportiveText }}</p>
        </div>

        <!-- 음성 오브(시각화) -->
        <div class="orb-stage" aria-hidden="true">
          <div class="orb-frame">
            <VoiceOrb :state="visualState" :size="340" />
          </div>
        </div>

        <!-- 자막 카드(내 말) -->
        <div v-if="transcriptText" class="caption-card" aria-live="polite">
          <span class="caption-label">내 말</span>
          <p class="caption-text">{{ transcriptText }}</p>
        </div>
      </section>

      <!-- 하단 컨트롤 -->
      <footer class="chat-controls">
        <div class="control-card">
          <!-- 마이크 버튼 -->
          <button
            class="mic-control"
            :class="{ listening: isListening, disabled: isMicDisabled }"
            :disabled="isMicDisabled"
            type="button"
            @click="handleMicClick"
            aria-label="마이크 버튼"
          >
            <span class="mic-ring"></span>
            <svg width="48" height="48" viewBox="0 0 24 24" aria-hidden="true">
              <path
                d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"
                fill="currentColor"
              />
              <path
                d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"
                fill="currentColor"
              />
            </svg>
          </button>
          <!-- 마이크 상태 라벨 -->
          <span class="mic-label">{{ micLabel }}</span>
        </div>
      </footer>
    </div>
  </div>
</template>

<style scoped>
/* 전체 레이아웃 리셋 */
.chat-viewport,
.chat-viewport * {
  box-sizing: border-box;
}

/* 화면 전체 배경과 중앙 정렬 */
.chat-viewport {
  height: 100vh;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at top, #f7f8f9 0%, #e6eaee 55%, #dfe3e8 100%);
  padding: 20px;
  overflow: hidden;
}

/* 중앙 컨테이너 크기/정렬 */
.chat-container {
  width: 100%;
  max-width: 500px;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 18px;
  color: #2e2e2e;
  padding: 8px 4px 12px;
}

/* 상단 버튼 정렬 */
.chat-top {
  display: flex;
  justify-content: flex-end;
}

/* 대화 종료 버튼 스타일 */
.end-button {
  min-height: 52px;
  padding: 12px 20px;
  border-radius: 20px;
  border: 2px solid rgba(255, 138, 128, 0.35);
  background: #f9fafb;
  color: #d66a61;
  font-size: 18px;
  font-weight: 800;
  cursor: pointer;
  box-shadow: 6px 6px 12px #d1d9e6, -6px -6px 12px #ffffff;
}

/* 본문 레이아웃 */
.chat-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  text-align: center;
  overflow: hidden;
}

/* AI 안내 카드 */
.ai-card {
  width: 100%;
  padding: 18px 20px;
  border-radius: 26px;
  background: #f5f6f7;
  box-shadow: 12px 12px 24px #cfd6df, -12px -12px 24px #ffffff;
  display: grid;
  gap: 10px;
}

/* AI 안내 라벨 */
.ai-label {
  font-size: 18px;
  font-weight: 700;
  color: #4cb7b7;
  letter-spacing: 0.4px;
}

/* 메인 메시지 */
.ai-message {
  font-size: 30px;
  font-weight: 900;
  line-height: 1.4;
  margin: 0;
}

/* 보조 메시지 */
.ai-sub {
  font-size: 22px;
  font-weight: 700;
  line-height: 1.5;
  margin: 0;
  color: #4cb7b7;
}

/* 오브(시각화) 영역 */
.orb-stage {
  width: 100%;
  flex: 1;
  min-height: 260px;
  border-radius: 32px;
  background: linear-gradient(145deg, #f7f9fa, #eef2f5);
  box-shadow: inset 8px 8px 18px rgba(209, 217, 230, 0.7), inset -8px -8px 18px #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
  overflow: hidden;
}

/* 오브 프레임(내부 배경) */
.orb-frame {
  width: 100%;
  height: 100%;
  border-radius: 28px;
  background: radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.9), rgba(245, 246, 247, 0.7) 70%);
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 내 말 자막 카드 */
.caption-card {
  width: 100%;
  display: grid;
  gap: 8px;
  padding: 14px 16px;
  border-radius: 22px;
  background: #ffffff;
  box-shadow: inset 4px 4px 10px rgba(209, 217, 230, 0.6), inset -4px -4px 10px #ffffff;
}

/* 자막 라벨 */
.caption-label {
  font-size: 18px;
  font-weight: 700;
  color: #1f5f5f;
}

/* 자막 텍스트 */
.caption-text {
  font-size: 22px;
  line-height: 1.6;
  margin: 0;
  color: #2e2e2e;
}

/* 하단 컨트롤 영역 */
.chat-controls {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding-bottom: calc(8px + env(safe-area-inset-bottom));
}

/* 컨트롤 카드 */
.control-card {
  width: 100%;
  padding: 16px 20px;
  border-radius: 26px;
  background: #f5f6f7;
  box-shadow: 12px 12px 24px #cfd6df, -12px -12px 24px #ffffff;
  display: grid;
  justify-items: center;
  gap: 10px;
}

/* 마이크 버튼 기본 상태 */
.mic-control {
  width: 118px;
  height: 118px;
  border-radius: 50%;
  border: 2px solid #4cb7b7;
  background: #f5f6f7;
  color: #4cb7b7;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  box-shadow: 12px 12px 24px #cfd6df, -12px -12px 24px #ffffff;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

/* 마이크 링(청취 중 애니메이션 용) */
.mic-control .mic-ring {
  position: absolute;
  inset: -8px;
  border-radius: 50%;
  border: 2px solid rgba(76, 183, 183, 0.5);
  opacity: 0;
}

/* 청취 중 상태 스타일 */
.mic-control.listening {
  background: #ff8a80;
  border-color: #ff8a80;
  color: #ffffff;
  box-shadow: 0 18px 36px rgba(255, 138, 128, 0.4);
}

/* 청취 중 링 애니메이션 */
.mic-control.listening .mic-ring {
  opacity: 1;
  animation: micPulse 1.4s ease-out infinite;
}

/* 비활성화 상태 */
.mic-control.disabled {
  opacity: 0.6;
  cursor: not-allowed;
  box-shadow: none;
}

/* 클릭 피드백 */
.mic-control:active:not(.disabled) {
  transform: scale(0.96);
}

/* 마이크 라벨 */
.mic-label {
  font-size: 18px;
  font-weight: 700;
  color: #4d4d4d;
}

/* 마이크 펄스 애니메이션 */
@keyframes micPulse {
  0% { transform: scale(0.95); opacity: 0.6; }
  100% { transform: scale(1.2); opacity: 0; }
}

/* 모션 최소화 설정 대응 */
@media (prefers-reduced-motion: reduce) {
  .mic-control .mic-ring {
    animation: none !important;
    transition: none !important;
  }
}
</style>
