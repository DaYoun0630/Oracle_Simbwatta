import type { Relationship, RoleCode } from "@/stores/signup";
import { registerWithPassword, verifySubjectLinkCodeApi } from "@/api/auth";

export interface SignupTermsPayload {
  agree_service: boolean;
  agree_privacy: boolean;
  agree_marketing: boolean;
}

export interface SignupApiPayload {
  role_code: RoleCode;
  name: string;
  email: string;
  phone_number: string;
  date_of_birth: string;
  password: string;
  gender?: "male" | "female";
  relationship?: Relationship;
  relationship_detail?: string;
  subject_link_code?: string;
  department?: string;
  license_number?: string;
  hospital?: string;
  hospital_number?: string;
  terms: SignupTermsPayload;
}

export interface SignupApiResponse {
  user_id: string;
  message: string;
}

export interface SubjectLinkCodeResult {
  valid: boolean;
  message: string;
  linked_subject_name?: string;
}

export async function verifySubjectLinkCode(code: string): Promise<SubjectLinkCodeResult> {
  const normalizedCode = code.trim();
  if (!normalizedCode) {
    return {
      valid: false,
      message: "대상자 회원번호를 입력해 주세요.",
    };
  }

  try {
    return await verifySubjectLinkCodeApi(normalizedCode);
  } catch (error) {
    console.error("verifySubjectLinkCode API failed:", error);
    return {
      valid: false,
      message: "회원번호 확인 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
    };
  }
}

export async function signupWithMockApi(payload: SignupApiPayload): Promise<SignupApiResponse> {
  if (!payload.terms.agree_service || !payload.terms.agree_privacy) {
    throw new Error("필수 약관 동의가 필요합니다.");
  }

  const response = await registerWithPassword(payload as unknown as Record<string, unknown>);
  return {
    user_id: String(response.user?.id ?? ""),
    message: "회원가입이 완료되었습니다.",
  };
}
