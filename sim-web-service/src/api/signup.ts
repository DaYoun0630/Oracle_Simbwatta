import type { Relationship, RoleCode } from "@/stores/signup";

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

const MOCK_DELAY_MS = 700;
const VALID_SUBJECT_CODES: Record<string, string> = {
  "LINK-1200": "김영희",
  "LINK-5521": "박민수",
  "LINK-8910": "이정은",
};

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const MEMBER_NUMBER_REGEX = /^SM-\d{6}$/;

// 보호자 대상자 회원번호 유효성 검증 Mock API
export async function verifySubjectLinkCode(code: string): Promise<SubjectLinkCodeResult> {
  await sleep(MOCK_DELAY_MS);

  const normalizedCode = code.trim().toUpperCase();
  if (!normalizedCode) {
    return {
      valid: false,
      message: "대상자 회원번호를 입력해 주세요.",
    };
  }

  if (MEMBER_NUMBER_REGEX.test(normalizedCode)) {
    return {
      valid: true,
      linked_subject_name: "대상자",
      message: "유효한 대상자 회원번호입니다.",
    };
  }

  const linkedSubjectName = VALID_SUBJECT_CODES[normalizedCode];
  if (!linkedSubjectName) {
    return {
      valid: false,
      message: "유효하지 않은 대상자 회원번호입니다. 다시 확인해 주세요.",
    };
  }

  return {
    valid: true,
    linked_subject_name: linkedSubjectName,
    message: `연결 가능한 대상자: ${linkedSubjectName}`,
  };
}

// 회원가입 Mock API
export async function signupWithMockApi(payload: SignupApiPayload): Promise<SignupApiResponse> {
  await sleep(MOCK_DELAY_MS + 300);

  if (!payload.terms.agree_service || !payload.terms.agree_privacy) {
    throw new Error("필수 약관 동의가 필요합니다.");
  }

  if (payload.role_code === 1 && payload.subject_link_code) {
    const verifyResult = await verifySubjectLinkCode(payload.subject_link_code);
    if (!verifyResult.valid) {
      throw new Error("대상자 회원번호 검증이 필요합니다.");
    }
  }

  return {
    user_id: `USR-${Date.now()}`,
    message: "회원가입이 완료되었습니다.",
  };
}
