import { ref, computed, readonly } from "vue";
import { sendChat } from "@/api/chat";

type VoiceState =
  | "idle"
  | "listening"
  | "processing"
  | "speaking";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

type SpeechRecognitionResultEvent = Event & {
  results: SpeechRecognitionResultList;
};

interface SpeechRecognitionLike extends EventTarget {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: ((event: SpeechRecognitionResultEvent) => void | Promise<void>) | null;
  onerror: ((event: Event) => void) | null;
  onend: ((event: Event) => void) | null;
  start: () => void;
  stop: () => void;
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

// 세션 상태
const state = ref<VoiceState>("idle");
const messages = ref<ChatMessage[]>([]);
const currentTranscript = ref("");
const currentResponse = ref("");
const sessionStartTime = ref<Date | null>(null);
const isSessionActive = ref(false);

// 타이머 관리
let listeningTimer: number | null = null;
let recognition: SpeechRecognitionLike | null = null;
let isRecognitionStopping = false;

const resetTimers = () => {
  if (listeningTimer) {
    clearTimeout(listeningTimer);
    listeningTimer = null;
  }
};

const stopRecognition = () => {
  if (!recognition) return;

  try {
    isRecognitionStopping = true;
    recognition.stop();
  } catch {
    // ignore stop failures when recognition is already closed
  }

  recognition = null;
};

// 메시지 ID 생성
const generateId = () =>
  `msg_${Date.now()}_${Math.random().toString(36).slice(2)}`;

export function useVoiceSession() {
  const isListening = computed(() => state.value === "listening");
  const isProcessing = computed(() => state.value === "processing");
  const isSpeaking = computed(() => state.value === "speaking");

  const startSession = () => {
    if (!isSessionActive.value) {
      sessionStartTime.value = new Date();
      isSessionActive.value = true;
      messages.value = [];
    }
  };

  // 음성 인식 시작
  const startListening = () => {
    startSession();
    resetTimers();
    stopRecognition();
    isRecognitionStopping = false;

    state.value = "listening";
    currentTranscript.value = "";
    currentResponse.value = "";

    const speechWindow = window as Window & {
      SpeechRecognition?: SpeechRecognitionConstructor;
      webkitSpeechRecognition?: SpeechRecognitionConstructor;
    };

    const SpeechRecognition =
      speechWindow.SpeechRecognition ||
      speechWindow.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      console.error("SpeechRecognition not supported");
      state.value = "idle";
      return;
    }

    recognition = new SpeechRecognition();
    recognition.lang = "ko-KR";
    recognition.interimResults = false;
    recognition.continuous = false;

    recognition.onresult = async (event) => {
      console.log("STT onresult fired");
      const transcript = event.results[0][0].transcript;
      console.log("STT transcript:", transcript);

      currentTranscript.value = transcript;

      messages.value.push({
        id: generateId(),
        role: "user",
        content: transcript,
        timestamp: new Date(),
      });

      await startProcessing(transcript);
    };

    recognition.onerror = (event) => {
      console.error("STT error", event);
      recognition = null;
      state.value = "idle";
    };

    recognition.onend = () => {
      console.log("STT ended");
      recognition = null;

      if (state.value === "listening" && !isRecognitionStopping) {
        state.value = "idle";
      }

      isRecognitionStopping = false;
    };

    console.log("SpeechRecognition start");

    recognition.start();

    listeningTimer = window.setTimeout(() => {
      stopRecognition();
      state.value = "idle";
    }, 10000);
  };

  // 백엔드 호출 단계
  const startProcessing = async (userText: string) => {
    resetTimers();
    stopRecognition();
    state.value = "processing";
    currentTranscript.value = "";
    console.log("CALL /chat", userText);

    try {
      const res = await sendChat(
        userText,
        {
          stage: "경도 인지 저하 의심",
          main_region: "해마",
          risk_level: "중간",
          trend: "최근 6개월간 소폭 저하",
          recommended_training: ["단어 회상"],
        },
        null
      );

      startSpeaking(res.response);
    } catch {
      state.value = "idle";
    }
  };

  // 음성 출력 단계
  const startSpeaking = (responseText: string) => {
    state.value = "speaking";
    currentResponse.value = responseText;

    messages.value.push({
      id: generateId(),
      role: "assistant",
      content: responseText,
      timestamp: new Date(),
    });

    const utterance = new SpeechSynthesisUtterance(responseText);
    utterance.lang = "ko-KR";
    utterance.rate = 0.9;

    utterance.onend = () => {
      finishSpeaking();
    };

    speechSynthesis.speak(utterance);
  };

  const finishSpeaking = () => {
    currentResponse.value = "";
    state.value = "idle";
  };

  const resetSession = () => {
    resetTimers();
    stopRecognition();
    state.value = "idle";
    messages.value = [];
    currentTranscript.value = "";
    currentResponse.value = "";
    sessionStartTime.value = null;
    isSessionActive.value = false;
  };

  const stopListening = () => {
    if (state.value !== "listening") return;
    resetTimers();
    stopRecognition();
    state.value = "idle";
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

    // Actions
    startListening,
    stopListening,
    finishSpeaking,
    resetSession,
  };
}
