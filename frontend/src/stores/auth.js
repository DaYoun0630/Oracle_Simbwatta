import { defineStore } from 'pinia';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null, // { id, name, role }
    accessToken: null,
  }),

  getters: {
    role: (state) => state.user?.role ?? null,
    userName: (state) => state.user?.name ?? '사용자',
    userId: (state) => state.user?.id ?? null,
    isAuthenticated: (state) => state.user !== null,
    token: (state) => state.accessToken,
  },

  actions: {
    // 역할 정규화 함수
    normalizeRole(role) {
      if (!role || typeof role !== 'string') return 'subject';
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
          name: '사용자',
          role: normalizedRole
        };
      } else {
        this.user.role = normalizedRole;
      }
      this.persist();
    },

    setSession(userData, accessToken) {
      this.user = {
        ...userData,
        role: this.normalizeRole(userData.role)
      };
      this.accessToken = accessToken || null;
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
      this.accessToken = null;
      localStorage.removeItem('auth-user');
    },

    // 로컬스토리지 저장
    persist() {
      if (this.user || this.accessToken) {
        localStorage.setItem('auth-user', JSON.stringify({
          user: this.user,
          accessToken: this.accessToken,
        }));
      }
    },

    // 앱 시작 시 복원
    hydrate() {
      const saved = localStorage.getItem('auth-user');
      if (saved) {
        try {
          const parsed = JSON.parse(saved);

          // Backward compatibility: old format stored only user object.
          const savedUser = parsed?.user ? parsed.user : parsed;
          this.accessToken = parsed?.accessToken ?? null;

          if (savedUser) {
            this.user = {
              ...savedUser,
              role: this.normalizeRole(savedUser.role)
            };
          } else {
            this.user = null;
          }
        } catch (e) {
          console.error('Failed to hydrate auth:', e);
          this.clear();
        }
      }
    }
  }
});
