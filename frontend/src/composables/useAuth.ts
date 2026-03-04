import { ref, computed } from "vue";

export type UserRole = "대상자" | "보호자" | "의료진" | null;

// 전역 상태 유지
const currentRole = ref<UserRole>(null);

export function useAuth() {
  const login = (role: UserRole) => {
    currentRole.value = role;
  };

  const logout = () => {
    currentRole.value = null;
  };

  const role = computed(() => currentRole.value);

  return {
    role,
    login,
    logout
  };
}