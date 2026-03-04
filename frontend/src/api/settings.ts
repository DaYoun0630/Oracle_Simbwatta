export interface AuthProfilePayload {
  id: number;
  email?: string | null;
  name?: string | null;
  role: "patient" | "caregiver" | "doctor";
  entity_id?: number | null;
  profile_image_url?: string | null;
  phone_number?: string | null;
  date_of_birth?: string | null;
  department?: string | null;
  license_number?: string | null;
  hospital?: string | null;
  hospital_number?: string | null;
}

export interface ProfileUpdatePayload {
  name?: string | null;
  phone_number?: string | null;
  date_of_birth?: string | null;
  profile_image_url?: string | null;
  department?: string | null;
  license_number?: string | null;
  hospital?: string | null;
  hospital_number?: string | null;
}

export interface UserSettingsPayload {
  notify_emergency: boolean;
  notify_weekly: boolean;
  notify_service: boolean;
  doctor_notify_risk: boolean;
  doctor_notify_weekly: boolean;
  doctor_notify_mri: boolean;
  share_dialog_summary: boolean;
  share_anomaly_alert: boolean;
  share_medication_reminder: boolean;
}

type UserSettingsUpdatePayload = Partial<UserSettingsPayload>;

const API_BASE_RAW = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");
const API_BASE = /\/api$/i.test(API_BASE_RAW) ? API_BASE_RAW : `${API_BASE_RAW}/api`;
const AUTH_BASE = `${API_BASE}/auth`;

const buildErrorFromResponse = async (res: Response, fallbackMessage: string) => {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string" && body.detail.trim()) {
      return new Error(body.detail);
    }
  } catch {
    // ignore JSON parse errors and use fallback message
  }
  return new Error(fallbackMessage);
};

const buildAuthHeaders = (token: string) => ({
  "Content-Type": "application/json",
  Authorization: `Bearer ${token}`,
});

export async function fetchAuthProfile(token: string): Promise<AuthProfilePayload> {
  const res = await fetch(`${AUTH_BASE}/profile`, {
    method: "GET",
    headers: buildAuthHeaders(token),
  });
  if (!res.ok) {
    throw await buildErrorFromResponse(res, "프로필 조회에 실패했습니다.");
  }
  return (await res.json()) as AuthProfilePayload;
}

export async function updateAuthProfile(
  token: string,
  payload: ProfileUpdatePayload
): Promise<AuthProfilePayload> {
  const res = await fetch(`${AUTH_BASE}/profile`, {
    method: "PUT",
    headers: buildAuthHeaders(token),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw await buildErrorFromResponse(res, "프로필 저장에 실패했습니다.");
  }
  return (await res.json()) as AuthProfilePayload;
}

export async function fetchUserSettings(token: string): Promise<UserSettingsPayload> {
  const res = await fetch(`${AUTH_BASE}/settings`, {
    method: "GET",
    headers: buildAuthHeaders(token),
  });
  if (!res.ok) {
    throw await buildErrorFromResponse(res, "설정 조회에 실패했습니다.");
  }
  return (await res.json()) as UserSettingsPayload;
}

export async function updateUserSettings(
  token: string,
  payload: UserSettingsUpdatePayload
): Promise<UserSettingsPayload> {
  const res = await fetch(`${AUTH_BASE}/settings`, {
    method: "PUT",
    headers: buildAuthHeaders(token),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw await buildErrorFromResponse(res, "설정 저장에 실패했습니다.");
  }
  return (await res.json()) as UserSettingsPayload;
}
