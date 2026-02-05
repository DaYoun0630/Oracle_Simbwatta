import { defineStore } from 'pinia';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null, // { id, name, role }
  }),

  getters: {
    role: (state) => state.user?.role ?? null,
    userName: (state) => state.user?.name ?? '사용자',
    userId: (state) => state.user?.id ?? null,
    isAuthenticated: (state) => state.user !== null,
  },

  actions: {
    // 역할 정규화 함수
    normalizeRole(role) {
      const normalized = role.toLowerCase();
      if (normalized === 'patient') return 'subject';
      if (normalized === 'caregiver') return 'caregiver';
      if (normalized === 'doctor') return 'doctor';
      return 'subject';
    },

    setRole(role) {
      const normalizedRole = this.normalizeRole(role);
      if (!this.user) {
        this.user = {
          id: 'temp-id',
          name: '김성신',
          role: normalizedRole
        };
      } else {
        this.user.role = normalizedRole;
      }
      this.persist();
    },

    setUser(userData) {
      this.user = {
        ...userData,
        role: this.normalizeRole(userData.role)
      };
      this.persist();
    },

    clear() {
      this.user = null;
      localStorage.removeItem('auth-user');
    },

    // 로컬스토리지 저장
    persist() {
      if (this.user) {
        localStorage.setItem('auth-user', JSON.stringify(this.user));
      }
    },

    // 앱 시작 시 복원
    hydrate() {
      const saved = localStorage.getItem('auth-user');
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          this.user = {
            ...parsed,
            role: this.normalizeRole(parsed.role)
          };
        } catch (e) {
          console.error('Failed to hydrate auth:', e);
          this.clear();
        }
      }
    }
  }
});