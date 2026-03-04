declare module "@/stores/auth" {
  export type AuthRole = "subject" | "caregiver" | "doctor" | null;

  export interface AuthUser {
    id: string | number;
    name: string;
    role: Exclude<AuthRole, null>;
    email?: string | null;
    entity_id?: number | null;
    profile_image_url?: string | null;
    phone_number?: string | null;
    date_of_birth?: string | null;
    department?: string | null;
    license_number?: string | null;
    hospital?: string | null;
    hospital_number?: string | null;
  }

  export interface AuthStore {
    user: AuthUser | null;
    accessToken: string | null;
    role: AuthRole;
    userName: string;
    userId: string | number | null;
    isAuthenticated: boolean;
    token: string | null;
    normalizeRole(role: string): Exclude<AuthRole, null>;
    setRole(role: string): void;
    setSession(userData: AuthUser, accessToken: string): void;
    setUser(userData: AuthUser): void;
    clear(): void;
    persist(): void;
    hydrate(): void;
  }

  export function useAuthStore(): AuthStore;
}
