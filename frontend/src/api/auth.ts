export interface AuthApiUser {
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

export interface AuthApiResponse {
  access_token: string;
  token_type: string;
  user: AuthApiUser;
}

export interface PasswordLoginPayload {
  email: string;
  password: string;
}

const API_BASE_RAW = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");
const API_BASE = /\/api$/i.test(API_BASE_RAW) ? API_BASE_RAW : `${API_BASE_RAW}/api`;
const AUTH_BASE = `${API_BASE}/auth`;

const DEFAULT_ERROR_MESSAGE = "요청 처리 중 오류가 발생했습니다.";

const buildErrorFromResponse = async (res: Response, fallbackMessage = DEFAULT_ERROR_MESSAGE) => {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string" && body.detail.trim()) {
      return new Error(body.detail);
    }
  } catch {
    // Ignore JSON parsing errors and use fallback.
  }

  return new Error(fallbackMessage);
};

export async function loginWithPassword(payload: PasswordLoginPayload): Promise<AuthApiResponse> {
  const res = await fetch(`${AUTH_BASE}/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw await buildErrorFromResponse(res, "로그인에 실패했습니다.");
  }

  return (await res.json()) as AuthApiResponse;
}

export async function registerWithPassword(payload: Record<string, unknown>): Promise<AuthApiResponse> {
  const res = await fetch(`${AUTH_BASE}/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw await buildErrorFromResponse(res, "회원가입에 실패했습니다.");
  }

  return (await res.json()) as AuthApiResponse;
}

export async function verifySubjectLinkCodeApi(subjectLinkCode: string): Promise<{
  valid: boolean;
  message: string;
  linked_subject_name?: string;
}> {
  const res = await fetch(`${AUTH_BASE}/verify-subject-link`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      subject_link_code: subjectLinkCode,
    }),
  });

  if (!res.ok) {
    throw await buildErrorFromResponse(res, "대상자 회원번호 확인에 실패했습니다.");
  }

  return (await res.json()) as {
    valid: boolean;
    message: string;
    linked_subject_name?: string;
  };
}
