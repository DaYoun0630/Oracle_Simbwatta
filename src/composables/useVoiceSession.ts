import { computed, readonly, ref } from "vue";
import {
  endChatSession,
  sendChat,
  startChatSession,
  type ChatMetaPayload,
} from "@/api/chat";

type VoiceState = "idle" | "speaking" | "listening" | "processing";
type SessionEndReason = "manual_stop" | "target_reached" | "reset";
type DialogStatePayload = Record<string, unknown> | null;
type ConversationPhase = "opening" | "warmup" | "dialog" | "closing";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

type SpeechRecognitionResultEvent = Event & {
  results: SpeechRecognitionResultList;
};

type SpeechRecognitionErrorEvent = Event & {
  error?: string;
};

interface SpeechRecognitionLike extends EventTarget {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: ((event: SpeechRecognitionResultEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: ((event: Event) => void) | null;
  start: () => void;
  stop: () => void;
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

const SESSION_LIMIT_MS = 300_000;
const SESSION_LIMIT_SEC = 300;
const WARMUP_END_SEC = 45;
const SOFT_WRAP_START_SEC = 240;
const LISTEN_RETRY_DELAY_MS = 350;
const PROFILE_ID_STORAGE_KEY = "voice_profile_id";
const SPEECH_SILENCE_COMMIT_MS = 1300;
const STT_NO_SPEECH_RETRY_LIMIT = 1;
const NO_SPEECH_GRACE_RETRIES = 1;
const NO_SPEECH_RETRY_DELAY_MS = 700;
const MIC_LEVEL_SENSITIVITY = 6.4;
const MIC_LEVEL_SILENCE_FLOOR = 0.022;
const MIC_ACTIVE_THRESHOLD = 0.024;
const SPEAKING_ACTIVE_THRESHOLD = 0.045;
const SPEAKING_LEVEL_INTERVAL_MS = 50;
const NO_SPEECH_PROMPT =
  "잘 못 들었어요. 다시 한번 말씀해 주세요.";

const OPENING_FALLBACK =
  "안녕하세요. 오늘도 만나서 반가워요. 먼저 가볍게 일상 이야기를 나눠볼까요?";

const CLOSING_FALLBACK =
  "오늘 대화 정말 잘해주셨어요. 수고 많으셨고, 다음에도 편하게 이야기해요.";

const DEFAULT_MODEL_RESULT: Record<string, unknown> = {
  stage: "경도 인지저하 의심 단계",
  main_region: "측두엽",
  risk_level: "중간",
  trend: "최근 수개월 동안 큰 변화 없이 유지",
  recommended_training: ["기억 회상", "언어 유창성"],
};

const state = ref<VoiceState>("idle");
const messages = ref<ChatMessage[]>([]);
const currentTranscript = ref("");
const currentResponse = ref("");
const sessionStartTime = ref<Date | null>(null);
const isSessionActive = ref(false);
const sessionId = ref<string | null>(null);
const dialogState = ref<DialogStatePayload>(null);
const turnIndex = ref(0);
const voiceLevel = ref(0);
const isVoiceActive = ref(false);

const conversationPhase = ref<ConversationPhase>("opening");

let sessionTimer: number | null = null;
let softWrapTimer: number | null = null;
let activeUtterance: SpeechSynthesisUtterance | null = null;
let resolveSpeaking: (() => void) | null = null;
let sessionToken = 0;
let recognition: SpeechRecognitionLike | null = null;
let isRecognitionStopping = false;
let silenceCommitTimer: number | null = null;
let stableTranscriptBuffer = "";
let interimTranscriptBuffer = "";
let micStream: MediaStream | null = null;
let micAudioContext: AudioContext | null = null;
let micAnalyser: AnalyserNode | null = null;
let micSourceNode: MediaStreamAudioSourceNode | null = null;
let micWaveData: Uint8Array<ArrayBuffer> | null = null;
let micMeterRaf: number | null = null;
let micMeterToken = 0;
let speakingLevelTimer: number | null = null;
let speakingLevelPhase = 0;
let noSpeechRetryCount = 0;
let sttNoSpeechRetryCount = 0;

const generateId = () =>
  `msg_${Date.now()}_${Math.random().toString(36).slice(2)}`;

const generateSessionId = () =>
  `session_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;

const getOrCreateProfileId = () => {
  if (typeof window === "undefined" || !window.localStorage) return undefined;

  const existing = window.localStorage.getItem(PROFILE_ID_STORAGE_KEY)?.trim();
  if (existing) return existing;

  const next = `profile_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
  window.localStorage.setItem(PROFILE_ID_STORAGE_KEY, next);
  return next;
};

const getElapsedMilliseconds = () => {
  if (!sessionStartTime.value) return 0;
  return Date.now() - sessionStartTime.value.getTime();
};

const getElapsedSeconds = () => Math.floor(getElapsedMilliseconds() / 1000);

const hasTimedOut = () => getElapsedMilliseconds() >= SESSION_LIMIT_MS;

const isCurrentSession = (token: number) =>
  isSessionActive.value && token === sessionToken;

const clamp01 = (value: number) => Math.min(1, Math.max(0, value));

const setAwaitingInputState = () => {
  state.value = isSessionActive.value ? "listening" : "idle";
};

const clearSessionTimer = () => {
  if (sessionTimer === null) return;
  clearTimeout(sessionTimer);
  sessionTimer = null;
};

const clearSoftWrapTimer = () => {
  if (softWrapTimer === null) return;
  clearTimeout(softWrapTimer);
  softWrapTimer = null;
};

const settleSpeakingPromise = () => {
  activeUtterance = null;
  if (!resolveSpeaking) return;
  const resolve = resolveSpeaking;
  resolveSpeaking = null;
  resolve();
};

const stopSpeakingLevelMeter = (resetLevel = true) => {
  if (speakingLevelTimer !== null) {
    clearInterval(speakingLevelTimer);
    speakingLevelTimer = null;
  }
  if (resetLevel) {
    voiceLevel.value = 0;
    isVoiceActive.value = false;
  }
};

const startSpeakingLevelMeter = () => {
  stopSpeakingLevelMeter(false);
  speakingLevelPhase = 0;
  isVoiceActive.value = false;

  speakingLevelTimer = window.setInterval(() => {
    const hasSpeechSynthesis =
      typeof window !== "undefined" && "speechSynthesis" in window;
    const isSynthSpeaking =
      hasSpeechSynthesis &&
      window.speechSynthesis.speaking &&
      !window.speechSynthesis.paused;

    if (!isSynthSpeaking) {
      const decayed = voiceLevel.value * 0.82;
      voiceLevel.value = decayed < 0.008 ? 0 : decayed;
      isVoiceActive.value = voiceLevel.value > SPEAKING_ACTIVE_THRESHOLD;
      return;
    }

    speakingLevelPhase += 0.22;
    const pulseA = Math.max(0, Math.sin(speakingLevelPhase)) * 0.22;
    const pulseB = Math.max(0, Math.sin(speakingLevelPhase * 1.5 + 0.35)) * 0.12;
    const target = clamp01(0.05 + pulseA + pulseB);
    const next = voiceLevel.value * 0.74 + target * 0.26;
    voiceLevel.value = clamp01(next);
    isVoiceActive.value = next > SPEAKING_ACTIVE_THRESHOLD;
  }, SPEAKING_LEVEL_INTERVAL_MS);
};

const stopMicMeterLoop = () => {
  if (micMeterRaf === null) return;
  cancelAnimationFrame(micMeterRaf);
  micMeterRaf = null;
};

const stopMicMeter = (resetLevel = true) => {
  micMeterToken += 1;
  stopMicMeterLoop();
  if (resetLevel) {
    voiceLevel.value = 0;
    isVoiceActive.value = false;
  }
};

const releaseMicMeterResources = async () => {
  stopMicMeter(false);

  if (micSourceNode) {
    try {
      micSourceNode.disconnect();
    } catch {
      // noop
    }
    micSourceNode = null;
  }

  micAnalyser = null;
  micWaveData = null;

  if (micStream) {
    micStream.getTracks().forEach((track) => track.stop());
    micStream = null;
  }

  if (micAudioContext) {
    try {
      await micAudioContext.close();
    } catch {
      // noop
    }
    micAudioContext = null;
  }
};

const ensureMicMeter = async () => {
  if (typeof window === "undefined" || !navigator.mediaDevices?.getUserMedia) {
    return false;
  }

  if (!micAudioContext) {
    micAudioContext = new window.AudioContext();
  }

  if (micAudioContext.state === "suspended") {
    await micAudioContext.resume();
  }

  if (!micStream) {
    micStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
  }

  if (!micAnalyser) {
    micAnalyser = micAudioContext.createAnalyser();
    micAnalyser.fftSize = 512;
    micAnalyser.smoothingTimeConstant = 0.78;
    micWaveData = new Uint8Array(micAnalyser.fftSize);
  }

  if (!micSourceNode) {
    micSourceNode = micAudioContext.createMediaStreamSource(micStream);
    micSourceNode.connect(micAnalyser);
  }

  return true;
};

const startMicMeter = async (token: number) => {
  stopSpeakingLevelMeter(false);

  try {
    const ready = await ensureMicMeter();
    if (!ready || !micAnalyser || !micWaveData) return;
  } catch (error) {
    console.error("Mic meter init failed", error);
    return;
  }

  const localMeterToken = ++micMeterToken;
  stopMicMeterLoop();

  const sample = () => {
    if (
      !isCurrentSession(token) ||
      state.value !== "listening" ||
      localMeterToken !== micMeterToken ||
      !micAnalyser ||
      !micWaveData
    ) {
      stopMicMeterLoop();
      return;
    }

    micAnalyser.getByteTimeDomainData(micWaveData);

    let energy = 0;
    for (let i = 0; i < micWaveData.length; i += 1) {
      const normalized = (micWaveData[i] - 128) / 128;
      energy += normalized * normalized;
    }

    const rms = Math.sqrt(energy / micWaveData.length);
    const measuredRaw = clamp01(Math.pow(rms * MIC_LEVEL_SENSITIVITY, 0.78));
    const measured = measuredRaw > MIC_LEVEL_SILENCE_FLOOR ? measuredRaw : 0;
    const next = voiceLevel.value * 0.56 + measured * 0.44;
    voiceLevel.value = clamp01(next);
    isVoiceActive.value = next > MIC_ACTIVE_THRESHOLD;

    micMeterRaf = window.requestAnimationFrame(sample);
  };

  micMeterRaf = window.requestAnimationFrame(sample);
};

const cancelSpeaking = () => {
  stopSpeakingLevelMeter();
  if (typeof window !== "undefined" && "speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
  settleSpeakingPromise();
};

const isRecognitionActive = () => recognition !== null;

const clearSilenceCommitTimer = () => {
  if (silenceCommitTimer === null) return;
  clearTimeout(silenceCommitTimer);
  silenceCommitTimer = null;
};

const clearRecognitionBuffers = () => {
  stableTranscriptBuffer = "";
  interimTranscriptBuffer = "";
};

const composeBufferedTranscript = () =>
  [stableTranscriptBuffer, interimTranscriptBuffer].filter(Boolean).join(" ").trim();

const isLikelyFillerUtterance = (text: string) => {
  const normalized = text.replace(/\s+/g, "").toLowerCase();
  if (!normalized) return true;
  const fillers = ["음", "어", "응", "아", "그", "저", "그러니까", "그니까", "음음"];
  return fillers.includes(normalized) || normalized.length <= 1;
};

const stopRecognition = () => {
  stopMicMeter();
  clearSilenceCommitTimer();
  if (!recognition) return;

  try {
    isRecognitionStopping = true;
    recognition.stop();
  } catch {
    // already stopped
  }

  recognition = null;
};

const appendUserMessage = (text: string) => {
  messages.value.push({
    id: generateId(),
    role: "user",
    content: text,
    timestamp: new Date(),
  });
};

const appendAssistantMessage = (text: string) => {
  messages.value.push({
    id: generateId(),
    role: "assistant",
    content: text,
    timestamp: new Date(),
  });
};

const normalizeConversationPhase = (
  value: unknown
): ConversationPhase | null => {
  const phase = String(value ?? "").trim().toLowerCase();
  if (phase === "opening") return "opening";
  if (phase === "warmup") return "warmup";
  if (phase === "dialog") return "dialog";
  if (phase === "closing") return "closing";
  return null;
};

const inferPhaseByTime = (elapsedSec: number): ConversationPhase => {
  if (elapsedSec >= SOFT_WRAP_START_SEC) return "closing";
  if (elapsedSec < WARMUP_END_SEC) return "warmup";
  return "dialog";
};

const shouldRequestClose = (elapsedSec: number) => {
  if (elapsedSec >= SESSION_LIMIT_SEC - 8) return true;
  return elapsedSec >= SOFT_WRAP_START_SEC;
};

const buildMetaPayload = (source: string, requestClose: boolean): ChatMetaPayload => {
  const elapsedSec = getElapsedSeconds();
  const inferredPhase = inferPhaseByTime(elapsedSec);

  let phase: ConversationPhase;
  if (source === "session_start") {
    phase = "opening";
  } else {
    phase = conversationPhase.value;
    if (phase === "opening") {
      phase = inferredPhase;
    } else if (inferredPhase === "closing") {
      phase = "closing";
    }
  }
  if (requestClose) {
    phase = "closing";
  }
  conversationPhase.value = phase;

  return {
    session_id: sessionId.value ?? undefined,
    profile_id: getOrCreateProfileId(),
    session_mode: "live",
    turn_index: turnIndex.value,
    elapsed_sec: elapsedSec,
    remaining_sec: Math.max(0, SESSION_LIMIT_SEC - elapsedSec),
    target_sec: SESSION_LIMIT_SEC,
    hard_limit_sec: SESSION_LIMIT_SEC,
    should_wrap_up: elapsedSec >= SOFT_WRAP_START_SEC,
    source,
    conversation_phase: phase,
    request_close: requestClose,
  };
};

const stopIfTimedOut = async (token: number) => {
  if (!isCurrentSession(token)) return true;
  if (!hasTimedOut()) return false;
  await stopSession("target_reached");
  return true;
};

const containsClosingTone = (text: string) => {
  const compact = text.replace(/\s+/g, "");
  return ["수고", "잘하", "고마워", "마무리", "다음에", "오늘은여기까지"].some(
    (keyword) => compact.includes(keyword)
  );
};

const botSpeak = async (text: string, token: number) => {
  if (!isCurrentSession(token)) return false;

  stopMicMeter(false);
  startSpeakingLevelMeter();
  state.value = "speaking";
  currentResponse.value = text;
  appendAssistantMessage(text);

  if (typeof window === "undefined" || !("speechSynthesis" in window)) {
    await new Promise<void>((resolve) => {
      globalThis.setTimeout(resolve, Math.min(2500, 700 + text.length * 20));
    });
  } else {
    await new Promise<void>((resolve) => {
      const utterance = new SpeechSynthesisUtterance(text);
      activeUtterance = utterance;
      resolveSpeaking = resolve;
      utterance.lang = "ko-KR";
      utterance.rate = 0.95;

      const settle = () => {
        settleSpeakingPromise();
      };

      utterance.onend = settle;
      utterance.onerror = settle;
      window.speechSynthesis.speak(utterance);
    });
  }

  stopSpeakingLevelMeter();
  if (!isCurrentSession(token)) return false;
  currentResponse.value = "";
  setAwaitingInputState();
  return true;
};

const scheduleSoftWrapCue = (token: number) => {
  void token;
  clearSoftWrapTimer();
};

const scheduleRecognitionRetry = (
  token: number,
  delayMs = LISTEN_RETRY_DELAY_MS
) => {
  window.setTimeout(() => {
    if (!isCurrentSession(token)) return;
    if (state.value === "processing" || state.value === "speaking") return;
    if (isRecognitionActive()) return;
    startLiveRecognition(token);
  }, delayMs);
};

const handleNoSpeechDetected = async (token: number) => {
  if (!isCurrentSession(token)) return;
  if (state.value === "processing" || state.value === "speaking") return;

  if (noSpeechRetryCount < NO_SPEECH_GRACE_RETRIES) {
    noSpeechRetryCount += 1;
    scheduleRecognitionRetry(token, NO_SPEECH_RETRY_DELAY_MS);
    return;
  }

  noSpeechRetryCount = 0;
  const spoke = await botSpeak(NO_SPEECH_PROMPT, token);
  if (!spoke) return;
  if (await stopIfTimedOut(token)) return;

  scheduleRecognitionRetry(token);
};

const extractTranscriptFromResults = (results: SpeechRecognitionResultList) => {
  let stable = "";
  let interim = "";

  for (let i = 0; i < results.length; i += 1) {
    const segment = results[i][0]?.transcript?.trim();
    if (!segment) continue;
    if (results[i].isFinal) {
      stable += `${segment} `;
    } else {
      interim += `${segment} `;
    }
  }

  return {
    stable: stable.trim(),
    interim: interim.trim(),
  };
};

const startLiveRecognition = (token: number) => {
  if (!isCurrentSession(token)) return;
  if (hasTimedOut()) {
    void stopSession("target_reached");
    return;
  }

  if (isRecognitionActive()) return;
  if (typeof window === "undefined") return;

  const speechWindow = window as Window & {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  };
  const SpeechRecognition =
    speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.error("SpeechRecognition is not supported in this browser.");
    void stopSession("manual_stop");
    return;
  }

  stopSpeakingLevelMeter(false);
  clearSilenceCommitTimer();
  clearRecognitionBuffers();
  state.value = "listening";
  currentTranscript.value = "";
  void startMicMeter(token);

  const localRecognition = new SpeechRecognition();
  recognition = localRecognition;
  isRecognitionStopping = false;
  localRecognition.lang = "ko-KR";
  localRecognition.continuous = true;
  localRecognition.interimResults = true;

  const scheduleSilenceCommit = () => {
    clearSilenceCommitTimer();
    silenceCommitTimer = window.setTimeout(() => {
      if (!isCurrentSession(token)) return;

      const combined = composeBufferedTranscript();
      if (!combined) return;

      if (isLikelyFillerUtterance(combined)) {
        clearRecognitionBuffers();
        currentTranscript.value = "";
        return;
      }

      currentTranscript.value = combined;
      clearRecognitionBuffers();
      stopRecognition();
      void handleUserTurn(combined, token);
    }, SPEECH_SILENCE_COMMIT_MS);
  };

  localRecognition.onresult = (event) => {
    if (!isCurrentSession(token)) return;

    const next = extractTranscriptFromResults(event.results);
    stableTranscriptBuffer = next.stable;
    interimTranscriptBuffer = next.interim;

    const combined = composeBufferedTranscript();
    if (!combined) return;

    sttNoSpeechRetryCount = 0;
    noSpeechRetryCount = 0;
    currentTranscript.value = combined;
    scheduleSilenceCommit();
  };

  localRecognition.onerror = (event) => {
    if (recognition === localRecognition) {
      recognition = null;
    }
    clearSilenceCommitTimer();

    if (!isCurrentSession(token)) return;

    const errorCode = event.error ?? "unknown";
    console.error("STT error", errorCode, event);

    if (errorCode === "aborted") return;

    if (errorCode === "no-speech") {
      if (sttNoSpeechRetryCount < STT_NO_SPEECH_RETRY_LIMIT) {
        sttNoSpeechRetryCount += 1;
        setAwaitingInputState();
        scheduleRecognitionRetry(token, NO_SPEECH_RETRY_DELAY_MS);
        return;
      }

      sttNoSpeechRetryCount = 0;
      void handleNoSpeechDetected(token);
      return;
    }

    if (hasTimedOut()) {
      void stopSession("target_reached");
      return;
    }

    setAwaitingInputState();
    scheduleRecognitionRetry(token);
  };

  localRecognition.onend = () => {
    if (recognition === localRecognition) {
      recognition = null;
    }
    clearSilenceCommitTimer();

    if (isRecognitionStopping) {
      isRecognitionStopping = false;
      return;
    }

    if (!isCurrentSession(token)) return;
    if (hasTimedOut()) {
      void stopSession("target_reached");
      return;
    }
    if (state.value === "processing" || state.value === "speaking") return;

    setAwaitingInputState();
    scheduleRecognitionRetry(token);
  };

  try {
    localRecognition.start();
  } catch (error) {
    console.error("Failed to start SpeechRecognition", error);
    if (!isCurrentSession(token)) return;
    scheduleRecognitionRetry(token, NO_SPEECH_RETRY_DELAY_MS);
  }
};

const handleUserTurn = async (transcript: string, token: number) => {
  if (!isCurrentSession(token)) return;
  if (await stopIfTimedOut(token)) return;

  noSpeechRetryCount = 0;
  sttNoSpeechRetryCount = 0;
  const elapsedBefore = getElapsedSeconds();
  const requestClose = shouldRequestClose(elapsedBefore);

  currentTranscript.value = transcript;
  appendUserMessage(transcript);
  turnIndex.value += 1;
  state.value = "processing";

  try {
    const response = await sendChat(
      transcript,
      DEFAULT_MODEL_RESULT,
      dialogState.value,
      buildMetaPayload("live_stt", requestClose)
    );

    if (!isCurrentSession(token)) return;

    if (response.session_id) {
      sessionId.value = response.session_id;
    }
    dialogState.value = response.state ?? dialogState.value;
    const backendPhase = normalizeConversationPhase(response.meta?.conversation_phase);
    if (backendPhase) {
      conversationPhase.value = backendPhase;
    }
    const backendRequestClose = Boolean(response.meta?.request_close);

    const spoke = await botSpeak(response.response, token);
    if (!spoke) return;

    if (backendRequestClose || requestClose) {
      conversationPhase.value = "closing";
      if (!containsClosingTone(response.response)) {
        const fallbackSpoke = await botSpeak(CLOSING_FALLBACK, token);
        if (!fallbackSpoke) return;
      }
      await stopSession("target_reached");
      return;
    }

    if (await stopIfTimedOut(token)) return;
    startLiveRecognition(token);
  } catch (error) {
    console.error("Chat request failed", error);
    if (!isCurrentSession(token)) return;
    await stopSession("manual_stop");
  }
};

const getOpeningMessage = async (token: number) => {
  try {
    const response = await startChatSession(
      DEFAULT_MODEL_RESULT,
      buildMetaPayload("session_start", false)
    );

    if (!isCurrentSession(token)) return OPENING_FALLBACK;

    if (response.session_id) {
      sessionId.value = response.session_id;
    }
    dialogState.value = response.state ?? dialogState.value;
    const backendPhase = normalizeConversationPhase(response.meta?.conversation_phase);
    if (backendPhase) {
      conversationPhase.value = backendPhase;
    }

    const opening = response.response?.trim();
    return opening || OPENING_FALLBACK;
  } catch (error) {
    console.error("Start chat request failed", error);
    return OPENING_FALLBACK;
  }
};

const startSessionTimer = (token: number) => {
  clearSessionTimer();
  sessionTimer = window.setTimeout(() => {
    if (!isCurrentSession(token)) return;
    void stopSession("target_reached");
  }, SESSION_LIMIT_MS);
};

const startSession = async () => {
  if (isSessionActive.value) return;

  sessionToken += 1;
  const token = sessionToken;

  state.value = "idle";
  isSessionActive.value = true;
  sessionStartTime.value = new Date();
  sessionId.value = generateSessionId();
  dialogState.value = null;
  turnIndex.value = 0;
  currentTranscript.value = "";
  currentResponse.value = "";
  messages.value = [];
  conversationPhase.value = "opening";
  noSpeechRetryCount = 0;
  sttNoSpeechRetryCount = 0;

  startSessionTimer(token);
  scheduleSoftWrapCue(token);

  const openingText = await getOpeningMessage(token);
  if (!isCurrentSession(token)) return;

  const spoke = await botSpeak(openingText, token);
  if (!spoke) return;
  if (await stopIfTimedOut(token)) return;

  startLiveRecognition(token);
};

const stopSession = async (reason: SessionEndReason, clearMessages = false) => {
  const endedSessionId = sessionId.value;
  const elapsedSec = getElapsedSeconds();
  const completedTurns = turnIndex.value;

  sessionToken += 1;
  clearSessionTimer();
  clearSoftWrapTimer();
  stopRecognition();
  cancelSpeaking();
  await releaseMicMeterResources();

  isSessionActive.value = false;
  state.value = "idle";
  currentTranscript.value = "";
  currentResponse.value = "";
  sessionStartTime.value = null;
  sessionId.value = null;
  dialogState.value = null;
  turnIndex.value = 0;
  conversationPhase.value = "opening";
  noSpeechRetryCount = 0;
  sttNoSpeechRetryCount = 0;

  if (clearMessages) {
    messages.value = [];
  }

  if (endedSessionId) {
    try {
      await endChatSession({
        session_id: endedSessionId,
        end_reason: reason,
        elapsed_sec: elapsedSec,
        turn_count: completedTurns,
        session_mode: "live",
      });
    } catch (error) {
      console.error("Session end request failed", error);
    }
  }
};

const resetSession = () => {
  if (!isSessionActive.value) {
    clearSessionTimer();
    clearSoftWrapTimer();
    stopRecognition();
    cancelSpeaking();
    void releaseMicMeterResources();
    state.value = "idle";
    currentTranscript.value = "";
    currentResponse.value = "";
    sessionStartTime.value = null;
    sessionId.value = null;
    dialogState.value = null;
    turnIndex.value = 0;
    conversationPhase.value = "opening";
    noSpeechRetryCount = 0;
    sttNoSpeechRetryCount = 0;
    messages.value = [];
    return;
  }

  void stopSession("reset", true);
};

export function useVoiceSession() {
  const isListening = computed(() => state.value === "listening");
  const isProcessing = computed(() => state.value === "processing");
  const isSpeaking = computed(() => state.value === "speaking");
  const isMockMode = computed(() => false);

  const startListening = () => {
    if (!isSessionActive.value) {
      void startSession();
      return;
    }

    if (state.value !== "idle") return;
    if (hasTimedOut()) {
      void stopSession("target_reached");
      return;
    }

    startLiveRecognition(sessionToken);
  };

  const stopListening = () => {
    if (!isSessionActive.value) return;
    void stopSession("manual_stop");
  };

  return {
    state: readonly(state),
    messages: readonly(messages),
    currentTranscript: readonly(currentTranscript),
    currentResponse: readonly(currentResponse),
    voiceLevel: readonly(voiceLevel),
    isVoiceActive: readonly(isVoiceActive),
    sessionStartTime: readonly(sessionStartTime),
    isSessionActive: readonly(isSessionActive),
    isListening,
    isProcessing,
    isSpeaking,
    isMockMode,
    startListening,
    stopListening,
    resetSession,
  };
}
