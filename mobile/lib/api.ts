import axios from 'axios';
import { authStorage } from './auth';

const BASE_URL = 'https://vps.zicore.space';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

// Inject token on every request
api.interceptors.request.use(async (config) => {
  const token = await authStorage.getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 globally
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401) {
      await authStorage.removeToken();
      // Navigation will handle redirect via AuthGate
    }
    return Promise.reject(error);
  }
);

/* ── Auth ─── */
export const authAPI = {
  login: (email: string, password: string) =>
    api.post('/api/sso/login', { email, password }),

  register: (name: string, email: string, password: string) =>
    api.post('/api/sso/register', { name, email, password }),

  me: () => api.get('/api/sso/me'),

  logout: () => api.post('/api/sso/logout'),

  changePassword: (old_password: string, new_password: string) =>
    api.post('/api/sso/change-password', { old_password, new_password }),

  sessions: () => api.get('/api/sso/sessions'),

  plans: () => api.get('/api/sso/plans'),

  stats: () => api.get('/api/sso/admin/stats'),
};

/* ── System ─── */
export const systemAPI = {
  stats: () => api.get('/api/system/stats'),
  status: () => api.get('/api/status'),
  nodeStatus: () => api.get('/api/node/status'),
};

/* ── ZIO Chat ─── */
export const chatAPI = {
  send: (message: string, sessionId?: string) =>
    api.post('/api/chat', { message, session_id: sessionId }),

  sendProvider: (provider: string, message: string) =>
    api.post('/api/provider/chat', { provider, message }),
};

/* ── Missions ─── */
export const missionsAPI = {
  list: () => api.get('/api/missions'),
  get: (id: string) => api.get(`/api/missions/${id}`),
  create: (data: any) => api.post('/api/missions', data),
  update: (id: string, data: any) => api.post(`/api/missions/${id}`, data),
  delete: (id: string) => api.delete(`/api/missions/${id}`),
};

/* ── Telemetry ─── */
export const telemetryAPI = {
  current: () => api.get('/api/telemetry'),
  modules: () => api.get('/api/telemetry/modules'),
};

/* ── Admin ─── */
export const adminAPI = {
  users: () => api.get('/api/sso/admin/users'),
  updateUser: (id: number, data: any) => api.put(`/api/sso/admin/user/${id}`, data),
  ollamaStatus: () => api.get('/api/ollama/status'),
};

/* ── ZiVR ─── */
export const zivrAPI = {
  config: () => api.get('/api/zivr/config'),
  generate: (prompt: string) => api.post('/api/zivr/generate', { prompt }),
  assets: () => api.get('/api/zivr/assets'),
};

export { BASE_URL };
export default api;
