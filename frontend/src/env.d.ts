/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_DOCTOR_USE_MOCK?: string
  readonly VITE_DOCTOR_AUTO_REFRESH_MS?: string
  readonly VITE_TREND_SOURCE?: "dummy" | "http"
  readonly VITE_VOICE_SESSION_MODE?: "live" | "mock"
  readonly VITE_VOICE_TARGET_SEC?: string
  readonly VITE_VOICE_HARD_LIMIT_SEC?: string
  readonly VITE_VOICE_MOCK_TURN_GAP_MS?: string
  readonly VITE_VOICE_MOCK_PREVIEW_MS?: string
  readonly VITE_VOICE_LIVE_TIMEOUT_MS?: string
  readonly VITE_VOICE_TIME_SCALE?: string
  readonly VITE_VOICE_MOCK_USE_TTS?: string
  readonly VITE_VOICE_LIVE_AUTO_RESUME?: string
  readonly VITE_VOICE_WRAP_UP_TURN_LIMIT?: string
  readonly VITE_VOICE_WRAP_UP_WINDOW_SEC?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare module "*.vue" {
  import type { DefineComponent } from "vue";
  const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, unknown>;
  export default component;
}
