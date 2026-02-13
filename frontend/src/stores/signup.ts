import { defineStore } from "pinia";
import {
  signupWithMockApi,
  verifySubjectLinkCode,
  type SignupApiPayload,
  type SignupApiResponse,
  type SignupTermsPayload,
} from "@/api/signup";

export type RoleCode = 0 | 1 | 2;
export type Gender = "male" | "female" | "";
export type Relationship =
  | "daughter"
  | "son"
  | "daughter_in_law"
  | "son_in_law"
  | "spouse"
  | "sibling"
  | "other"
  | "";

export interface SignupState {
  role_code: RoleCode | null;
  name: string;
  email: string;
  phone_number: string;
  date_of_birth: string;
  password: string;
  gender: Gender;
  relationship: Relationship;
  relationship_detail: string;
  subject_link_code: string;
  department: string;
  license_number: string;
  hospital: string;
  hospital_number: string;
  subjectCodeVerified: boolean;
  subjectCodeMessage: string;
  isCheckingSubjectCode: boolean;
  isSubmitting: boolean;
  lastSignupUserId: string;
}

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_REGEX = /^010-\d{4}-\d{4}$/;

const getInitialState = (): SignupState => ({
  role_code: null,
  name: "",
  email: "",
  phone_number: "",
  date_of_birth: "",
  password: "",
  gender: "",
  relationship: "",
  relationship_detail: "",
  subject_link_code: "",
  department: "",
  license_number: "",
  hospital: "",
  hospital_number: "",
  subjectCodeVerified: false,
  subjectCodeMessage: "",
  isCheckingSubjectCode: false,
  isSubmitting: false,
  lastSignupUserId: "",
});

const roleCodeToLabelMap: Record<RoleCode, string> = {
  0: "대상자",
  1: "보호자",
  2: "의사",
};

export const useSignupStore = defineStore("signup", {
  state: (): SignupState => getInitialState(),

  getters: {
    roleLabel: (state): string =>
      state.role_code === null ? "미선택" : roleCodeToLabelMap[state.role_code],

    isEmailValid: (state): boolean => EMAIL_REGEX.test(state.email.trim()),

    isPhoneValid: (state): boolean => PHONE_REGEX.test(state.phone_number.trim()),

    isPasswordValid: (state): boolean => state.password.trim().length >= 8,

    isCommonValid(state): boolean {
      return (
        state.name.trim().length > 0 &&
        this.isEmailValid &&
        this.isPhoneValid &&
        state.date_of_birth.trim().length > 0 &&
        this.isPasswordValid
      );
    },

    isRoleSpecificValid(state): boolean {
      if (state.role_code === null) return false;

      if (state.role_code === 0) {
        return state.gender !== "";
      }

      if (state.role_code === 1) {
        return (
          state.relationship !== "" &&
          (state.relationship !== "other" || state.relationship_detail.trim().length > 0) &&
          state.subject_link_code.trim().length > 0 &&
          state.subjectCodeVerified
        );
      }

      return (
        state.department.trim().length > 0 &&
        state.license_number.trim().length > 0 &&
        state.hospital.trim().length > 0 &&
        state.hospital_number.trim().length > 0
      );
    },

    canProceedToTerms(): boolean {
      return this.role_code !== null && this.isCommonValid && this.isRoleSpecificValid;
    },
  },

  actions: {
    setRole(roleCode: RoleCode): void {
      this.role_code = roleCode;
      this.clearRoleSpecificFields();
      this.subjectCodeVerified = false;
      this.subjectCodeMessage = "";
    },

    clearRoleSpecificFields(): void {
      this.gender = "";
      this.relationship = "";
      this.relationship_detail = "";
      this.subject_link_code = "";
      this.department = "";
      this.license_number = "";
      this.hospital = "";
      this.hospital_number = "";
      this.subjectCodeVerified = false;
      this.subjectCodeMessage = "";
    },

    resetSubjectCodeVerification(): void {
      this.subjectCodeVerified = false;
      this.subjectCodeMessage = "";
    },

    async validateSubjectLinkCode(): Promise<boolean> {
      if (this.role_code !== 1) return false;

      const normalizedCode = this.subject_link_code.trim();
      if (!normalizedCode) {
        this.subjectCodeVerified = false;
        this.subjectCodeMessage = "연동 코드를 입력해 주세요.";
        return false;
      }

      this.isCheckingSubjectCode = true;
      try {
        const result = await verifySubjectLinkCode(normalizedCode);
        this.subjectCodeVerified = result.valid;
        this.subjectCodeMessage = result.message;
        return result.valid;
      } catch (error) {
        console.error("Subject link validation failed:", error);
        this.subjectCodeVerified = false;
        this.subjectCodeMessage = "코드 확인 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.";
        return false;
      } finally {
        this.isCheckingSubjectCode = false;
      }
    },

    toApiPayload(terms: SignupTermsPayload): SignupApiPayload {
      if (this.role_code === null) {
        throw new Error("role_code is required");
      }

      return {
        role_code: this.role_code,
        name: this.name.trim(),
        email: this.email.trim(),
        phone_number: this.phone_number.trim(),
        date_of_birth: this.date_of_birth,
        password: this.password,
        gender: this.gender || undefined,
        relationship: this.relationship || undefined,
        relationship_detail: this.relationship_detail.trim() || undefined,
        subject_link_code: this.subject_link_code.trim() || undefined,
        department: this.department.trim() || undefined,
        license_number: this.license_number.trim() || undefined,
        hospital: this.hospital.trim() || undefined,
        hospital_number: this.hospital_number.trim() || undefined,
        terms,
      };
    },

    async submitSignup(terms: SignupTermsPayload): Promise<SignupApiResponse> {
      const payload = this.toApiPayload(terms);
      this.isSubmitting = true;

      try {
        const result = await signupWithMockApi(payload);
        this.lastSignupUserId = result.user_id;
        return result;
      } finally {
        this.isSubmitting = false;
      }
    },

    reset(): void {
      Object.assign(this, getInitialState());
    },
  },
});
