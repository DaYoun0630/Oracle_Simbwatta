const BASE_URL = import.meta.env.VITE_API_BASE_URL;

console.log("API BASE URL:", BASE_URL);

export type VoiceSessionMode = "live" | "mock";
export type ConversationMode = "daily" | "therapy" | "mixed";
export type SttEventType = "speech" | "no_speech" | "stt_error";

export interface ChatMetaPayload {
  session_id?: string;
  profile_id?: string;
  session_mode?: VoiceSessionMode;
  conversation_mode?: ConversationMode;
  session_event?: "session_start";
  stt_event?: SttEventType;
  closing_reason?: string;
  turn_index?: number;
  elapsed_sec?: number;
  remaining_sec?: number;
  target_sec?: number;
  hard_limit_sec?: number;
  should_wrap_up?: boolean;
  source?: string;
  conversation_phase?: "opening" | "warmup" | "dialog" | "closing";
  request_close?: boolean;
}

export interface ChatResponse {
  response: string;
  state: Record<string, unknown> | null;
  dialog_summary?: string | null;
  session_id?: string;
  meta?: {
    conversation_phase?: "opening" | "warmup" | "dialog" | "closing";
    turn_index?: number;
    request_close?: boolean;
    conversation_mode?: ConversationMode;
    stt_event?: SttEventType;
    closing_reason?: string;
    stimulus_count?: number;
    recall_hits?: number;
  } | null;
}

export interface EndSessionPayload {
  session_id: string;
  end_reason: string;
  elapsed_sec?: number;
  turn_count?: number;
  session_mode?: VoiceSessionMode;
}

export interface StartChatPayload {
  model_result: Record<string, unknown>;
  meta?: ChatMetaPayload | null;
}

export async function sendChat(
  userMessage: string,
  modelResult: Record<string, unknown>,
  state?: Record<string, unknown> | null,
  meta?: ChatMetaPayload
): Promise<ChatResponse> {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      user_message: userMessage,
      model_result: modelResult,
      state: state ?? null,
      meta: meta ?? null,
    }),
  });

  if (!res.ok) {
    throw new Error("Chat API failed");
  }

  return (await res.json()) as ChatResponse;
}

export async function endChatSession(payload: EndSessionPayload): Promise<void> {
  const res = await fetch(`${BASE_URL}/session/end`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error("Session end API failed");
  }
}

export async function startChatSession(
  modelResult: Record<string, unknown>,
  meta?: ChatMetaPayload
): Promise<ChatResponse> {
  const payload: StartChatPayload = {
    model_result: modelResult,
    meta: meta ?? null,
  };

  const res = await fetch(`${BASE_URL}/start`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error("Start Chat API failed");
  }

  return (await res.json()) as ChatResponse;
}
