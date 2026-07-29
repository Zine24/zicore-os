import axios from 'axios';
import { authStorage } from './auth';

const BASE_URL = 'http://192.168.1.85:4000';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use(async (config) => {
  const token = await authStorage.getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401) {
      await authStorage.removeToken();
    }
    return Promise.reject(error);
  }
);

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

export const systemAPI = {
  stats: () => api.get('/api/system/stats'),
  status: () => api.get('/api/status'),
  nodeStatus: () => api.get('/api/node/status'),
};

export const chatAPI = {
  send: (message: string, sessionId?: string) =>
    api.post('/api/chat', { message, session_id: sessionId }),

  sendProvider: (provider: string, message: string) =>
    api.post('/api/provider/chat', { provider, message }),
};

export const voiceAPI = {
  tts: (text: string, lang = 'es') =>
    api.post('/api/tts', { text, lang }, { responseType: 'blob', timeout: 60000 }),

  stt: (audioUri: string, lang = 'es') => {
    const form = new FormData();
    form.append('audio', { uri: audioUri, type: 'audio/m4a', name: 'recording.m4a' } as any);
    form.append('lang', lang);
    return api.post('/api/stt', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    });
  },
};

export const missionsAPI = {
  list: () => api.get('/api/missions'),
  get: (id: string) => api.get(`/api/missions/${id}`),
  create: (data: any) => api.post('/api/missions', data),
  update: (id: string, data: any) => api.post(`/api/missions/${id}`, data),
  delete: (id: string) => api.delete(`/api/missions/${id}`),
};

export const telemetryAPI = {
  current: () => api.get('/api/telemetry'),
  modules: () => api.get('/api/telemetry/modules'),
};

export const adminAPI = {
  users: () => api.get('/api/sso/admin/users'),
  updateUser: (id: number, data: any) => api.put(`/api/sso/admin/user/${id}`, data),
  ollamaStatus: () => api.get('/api/ollama/status'),
};

export const zivrAPI = {
  config: () => api.get('/api/zivr/config'),
  generate: (prompt: string) => api.post('/api/zivr/generate', { prompt }),
  assets: () => api.get('/api/zivr/assets'),
};

export { BASE_URL };
export default api;
