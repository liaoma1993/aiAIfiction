import { create } from 'zustand';
import { authApi } from '@/services/projectApi';

interface AuthState {
  user: any | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, username: string, password: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('token'),
  loading: false,

  login: async (email, password) => {
    set({ loading: true });
    const data = await authApi.login(email, password);
    localStorage.setItem('token', data.access_token);
    set({ token: data.access_token, user: { id: data.user_id, username: data.username }, loading: false });
  },

  register: async (email, username, password) => {
    set({ loading: true });
    const data = await authApi.register(email, username, password);
    localStorage.setItem('token', data.access_token);
    set({ token: data.access_token, user: { id: data.user_id, username: data.username }, loading: false });
  },

  logout: () => {
    localStorage.removeItem('token');
    set({ user: null, token: null });
  },

  checkAuth: () => {
    const token = localStorage.getItem('token');
    if (!token) set({ user: null, token: null });
  },
}));
