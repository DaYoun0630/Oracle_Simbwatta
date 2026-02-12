declare module "@/stores/auth" {
  export type AuthRole = "subject" | "caregiver" | "doctor" | null;

  export interface AuthUser {
    id: string;
    name: string;
    role: Exclude<AuthRole, null>;
  }

  export interface AuthStore {
    user: AuthUser | null;
    role: AuthRole;
    userName: string;
    userId: string | null;
    isAuthenticated: boolean;
    normalizeRole(role: string): Exclude<AuthRole, null>;
    setRole(role: string): void;
    setUser(userData: AuthUser): void;
    clear(): void;
    persist(): void;
    hydrate(): void;
  }

  export function useAuthStore(): AuthStore;
}
