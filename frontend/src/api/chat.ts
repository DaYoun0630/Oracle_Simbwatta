const API_BASE_RAW = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");
const BASE_URL = API_BASE_RAW || "/api";

console.log("API BASE URL:", BASE_URL);

const buildErrorFromResponse = async (res: Response, fallbackMessage: string) => {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string" && body.detail.trim()) {
      return new Error(body.detail);
    }
  } catch {
    // Ignore parse errors and use fallback message.
  }

  return new Error(`${fallbackMessage} (HTTP ${res.status})`);
};

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

export interface UploadSessionAudioResponse {
  ok: boolean;
  session_id: string;
  patient_id: string;
  audio_path: string;
  audio_format: string;
  converted_to_wav: boolean;
  conversion_error?: string | null;
  uploaded_at: string;
}

export async function sendChat(
  userMessage: string,
  modelResult: Record<string, unknown>,
  state?: Record<string, unknown> | null,
  meta?: ChatMetaPayload
): Promise<ChatResponse> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}/chat`, {
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
  } catch (error) {
    throw new Error("Bad connection to Chat API");
  }

  if (!res.ok) {
    throw await buildErrorFromResponse(res, "Chat API failed");
  }

  return (await res.json()) as ChatResponse;
}

export async function endChatSession(payload: EndSessionPayload): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}/session/end`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
  } catch (error) {
    throw new Error("Bad connection to Session End API");
  }

  if (!res.ok) {
    throw await buildErrorFromResponse(res, "Session end API failed");
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

  let res: Response;
  try {
    res = await fetch(`${BASE_URL}/start`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
  } catch (error) {
    throw new Error("Bad connection to Start Chat API");
  }

  if (!res.ok) {
    throw await buildErrorFromResponse(res, "Start Chat API failed");
  }

  return (await res.json()) as ChatResponse;
}

export async function uploadSessionAudio(
  sessionId: string,
  file: File,
  profileId?: string
): Promise<UploadSessionAudioResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("session_id", sessionId);
  if (profileId) {
    formData.append("profile_id", profileId);
  }

  let res: Response;
  try {
    res = await fetch(`${BASE_URL}/session/upload-audio`, {
      method: "POST",
      body: formData,
    });
  } catch (error) {
    throw new Error("Bad connection to Session Audio Upload API");
  }

  if (!res.ok) {
    throw await buildErrorFromResponse(res, "Session audio upload failed");
  }

  return (await res.json()) as UploadSessionAudioResponse;
}
