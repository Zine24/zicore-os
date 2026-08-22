import { create } from 'zustand';
import { authStorage } from '@/lib/auth';
import { authAPI } from '@/lib/api';

interface User {
  id: number;
  username: string;
  email: string;
  display_name: string;
  role: string;
  plan?: string;
  plan_info?: any;
}

interface AuthState {
  token: string | null;
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;

  init: () => Promise<void>;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  register: (name: string, email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  isLoading: true,
  isAuthenticated: false,

  init: async () => {
    try {
      const token = await authStorage.getToken();
      if (token) {
        const res = await authAPI.me();
        if (res.data?.status === 'ok') {
          set({ token, user: res.data.user, isAuthenticated: true, isLoading: false });
          return;
        }
      }
      set({ isLoading: false });
    } catch {
      await authStorage.clearAll();
      set({ isLoading: false });
    }
  },

  login: async (email, password) => {
    try {
      const res = await authAPI.login(email, password);
      const data = res.data;
      if (data.status === 'ok' && data.token) {
        await authStorage.setToken(data.token);
        await authStorage.setUser(data.user);
        set({ token: data.token, user: data.user, isAuthenticated: true });
        return { success: true };
      }
      return { success: false, error: data.error || 'Login failed' };
    } catch (err: any) {
      return { success: false, error: err.response?.data?.error || 'Network error' };
    }
  },

  register: async (name, email, password) => {
    try {
      const res = await authAPI.register(name, email, password);
      const data = res.data;
      if (data.status === 'ok' && data.token) {
        await authStorage.setToken(data.token);
        await authStorage.setUser(data.user);
        set({ token: data.token, user: data.user, isAuthenticated: true });
        return { success: true };
      }
      return { success: false, error: data.error || 'Registration failed' };
    } catch (err: any) {
      return { success: false, error: err.response?.data?.error || 'Network error' };
    }
  },

  logout: async () => {
    try { await authAPI.logout(); } catch {}
    await authStorage.clearAll();
    set({ token: null, user: null, isAuthenticated: false });
  },
}));
