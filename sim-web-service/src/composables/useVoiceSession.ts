import { ref, computed, readonly } from "vue";

type VoiceState =
  | "idle"
  | "listening"
  | "pause"
  | "processing"
  | "speaking";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

// 싱글톤 패턴: 모듈 레벨에서 state 관리
const state = ref<VoiceState>("idle");
const messages = ref<ChatMessage[]>([]);
const currentTranscript = ref(""); // 실시간 음성 인식 텍스트
const currentResponse = ref(""); // AI 응답 텍스트
const sessionStartTime = ref<Date | null>(null);
const isSessionActive = ref(false);

let listeningTimer: number | null = null;
let pauseTimer: number | null = null;
let processingTimer: number | null = null;
let typingTimer: number | null = null;

const resetTimers = () => {
  if (listeningTimer) clearTimeout(listeningTimer);
  if (pauseTimer) clearTimeout(pauseTimer);
  if (processingTimer) clearTimeout(processingTimer);
  if (typingTimer) clearInterval(typingTimer);

  listeningTimer = null;
  pauseTimer = null;
  processingTimer = null;
  typingTimer = null;
};

// 샘플 응답들 (실제로는 API에서 받아옴)
const sampleResponses = [
  "오늘 기분이 어떠세요? 편하게 말씀해 주세요.",
  "그렇군요. 더 자세히 이야기해 주실 수 있으신가요?",
  "말씀해 주셔서 감사합니다. 그런 감정을 느끼시는 건 자연스러운 일이에요.",
  "좋은 하루 보내고 계신 것 같아서 기쁘네요.",
  "힘드셨겠어요. 제가 더 도와드릴 수 있는 부분이 있을까요?"
];

// 샘플 사용자 발화 (실제로는 음성 인식에서)
const sampleUserMessages = [
  "오늘은 기분이 좋아요",
  "조금 피곤한 것 같아요",
  "요즘 잠을 잘 못 자요",
  "산책을 다녀왔어요",
  "가족들과 통화했어요"
];

const generateId = () => `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

// 타이핑 효과로 텍스트 표시
const typeText = (text: string, target: typeof currentTranscript | typeof currentResponse, onComplete?: () => void) => {
  let index = 0;
  target.value = "";

  typingTimer = window.setInterval(() => {
    if (index < text.length) {
      target.value += text[index];
      index++;
    } else {
      if (typingTimer) clearInterval(typingTimer);
      typingTimer = null;
      onComplete?.();
    }
  }, 60);
};

export function useVoiceSession() {
  const isListening = computed(() => state.value === "listening");
  const isProcessing = computed(() => state.value === "processing");
  const isSpeaking = computed(() => state.value === "speaking");
  const hasMessages = computed(() => messages.value.length > 0);

  const startSession = () => {
    if (!isSessionActive.value) {
      sessionStartTime.value = new Date();
      isSessionActive.value = true;
      messages.value = [];
    }
  };

  const startListening = () => {
    startSession();
    resetTimers();
    state.value = "listening";
    currentTranscript.value = "";
    currentResponse.value = "";

    // 랜덤 사용자 메시지 선택
    const randomUserMessage = sampleUserMessages[Math.floor(Math.random() * sampleUserMessages.length)];

    // 사용자가 말하는 것처럼 타이핑 효과
    typeText(randomUserMessage, currentTranscript, () => {
      // 타이핑 완료 후 잠시 대기
      pauseTimer = window.setTimeout(() => {
        // 사용자 메시지 추가
        messages.value.push({
          id: generateId(),
          role: "user",
          content: randomUserMessage,
          timestamp: new Date()
        });

        startProcessing();
      }, 960);
    });

    // 최대 listening 시간 (타임아웃)
    listeningTimer = window.setTimeout(() => {
      if (state.value === "listening") {
        startProcessing();
      }
    }, 9600);
  };

  const startProcessing = () => {
    resetTimers();
    state.value = "processing";
    currentTranscript.value = "";

    // AI가 생각 중인 시간
    processingTimer = window.setTimeout(() => {
      startSpeaking();
    }, 1800);
  };

  const startSpeaking = () => {
    state.value = "speaking";

    // 랜덤 AI 응답 선택
    const randomResponse = sampleResponses[Math.floor(Math.random() * sampleResponses.length)];

    // AI 응답 타이핑 효과
    typeText(randomResponse, currentResponse, () => {
      // 응답 완료 후 메시지 추가
      messages.value.push({
        id: generateId(),
        role: "assistant",
        content: randomResponse,
        timestamp: new Date()
      });

      // 잠시 후 idle 상태로
      setTimeout(() => {
        finishSpeaking();
      }, 1200);
    });
  };

  const finishSpeaking = () => {
    currentResponse.value = "";
    state.value = "idle";
  };

  const resetSession = () => {
    resetTimers();
    state.value = "idle";
    messages.value = [];
    currentTranscript.value = "";
    currentResponse.value = "";
    sessionStartTime.value = null;
    isSessionActive.value = false;
  };

  const stopListening = () => {
    if (state.value === "listening") {
      resetTimers();
      if (currentTranscript.value) {
        messages.value.push({
          id: generateId(),
          role: "user",
          content: currentTranscript.value,
          timestamp: new Date()
        });
        startProcessing();
      } else {
        state.value = "idle";
      }
    }
  };

  // 텍스트 메시지 직접 전송
  const sendTextMessage = (text: string) => {
    if (!text.trim()) return;

    startSession();

    messages.value.push({
      id: generateId(),
      role: "user",
      content: text.trim(),
      timestamp: new Date()
    });

    state.value = "processing";
    currentTranscript.value = "";

    processingTimer = window.setTimeout(() => {
      startSpeaking();
    }, 1800);
  };

  return {
    // State
    state: readonly(state),
    messages: readonly(messages),
    currentTranscript: readonly(currentTranscript),
    currentResponse: readonly(currentResponse),
    sessionStartTime: readonly(sessionStartTime),
    isSessionActive: readonly(isSessionActive),

    // Computed
    isListening,
    isProcessing,
    isSpeaking,
    hasMessages,

    // Actions
    startListening,
    stopListening,
    finishSpeaking,
    resetSession,
    sendTextMessage,
  };
}
