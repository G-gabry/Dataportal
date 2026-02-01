import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { User } from '@/types';

interface AuthState {
  token: string | null;
  user: User | null;
  _hasHydrated: boolean;
  setAuth: (token: string, user: User) => void;
  clearAuth: () => void;
  logout: () => void;
  isAuthenticated: () => boolean;
  setHasHydrated: (state: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      _hasHydrated: false,
      setAuth: (token: string, user: User) => {
        set({ token, user });
        if (typeof window !== 'undefined') {
          localStorage.setItem('token', token);
        }
      },
      clearAuth: () => {
        set({ token: null, user: null });
        if (typeof window !== 'undefined') {
          localStorage.removeItem('token');
        }
      },
      logout: () => {
        set({ token: null, user: null });
        if (typeof window !== 'undefined') {
          localStorage.removeItem('token');
          localStorage.removeItem('auth-storage');
          window.location.href = '/login';
        }
      },
      isAuthenticated: () => !!get().token,
      setHasHydrated: (state: boolean) => {
        set({ _hasHydrated: state });
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);
