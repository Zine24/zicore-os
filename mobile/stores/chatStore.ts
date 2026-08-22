import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';
import { BASE_URL } from '@/lib/api';
import { authStorage } from '@/lib/auth';
import { collectAndReturn } from '@/lib/sensorService';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  streaming?: boolean;
  mediaUrl?: string;
  mediaType?: string;
}

interface ChatState {
  messages: Message[];
  isLoading: boolean;
  sessionId: string;
  loaded: boolean;

  loadHistory: () => Promise<void>;
  sendMessage: (text: string) => Promise<void>;
  clearMessages: () => void;
}

const SESSION_KEY = 'zicore_session_id';

async function getStoredSession(): Promise<string> {
  try {
    const existing = await SecureStore.getItemAsync(SESSION_KEY);
    if (existing) return existing;
  } catch {}
  const fresh = 'mobile_' + Date.now();
  try {
    await SecureStore.setItemAsync(SESSION_KEY, fresh);
  } catch {}
  return fresh;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isLoading: false,
  sessionId: 'mobile_' + Date.now(),
  loaded: false,

  loadHistory: async () => {
    const sessionId = await getStoredSession();
    set({ sessionId });
    try {
      const token = await authStorage.getToken();
      const res = await fetch(
        `${BASE_URL}/api/knowledge/conversations?limit=100&session_id=${encodeURIComponent(sessionId)}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) return;
      const data = await res.json();
      const convs = Array.isArray(data.conversations) ? data.conversations : Array.isArray(data) ? data : [];
      if (!convs.length) return;
      const history: Message[] = convs.map((c: any) => ({
        id: (c.role === 'user' ? 'u_' : 'a_') + (c.timestamp || Date.now()) + '_' + Math.random().toString(36).slice(2, 7),
        role: c.role === 'user' ? 'user' : 'assistant',
        content: c.content || '',
        timestamp: c.timestamp || Date.now(),
        streaming: false,
      }));
      set({ messages: history, loaded: true });
    } catch {}
  },

  sendMessage: async (text: string) => {
    const userMsg: Message = {
      id: 'u_' + Date.now(),
      role: 'user',
      content: text,
      timestamp: Date.now(),
    };

    const assistantId = 'a_' + Date.now();
    const assistantMsg: Message = {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      streaming: true,
    };

    set((s) => ({
      messages: [...s.messages, userMsg, assistantMsg],
      isLoading: true,
    }));

    try {
      const token = await authStorage.getToken();
      const sensorData = await collectAndReturn().catch(() => ({}));
      const response = await fetch(`${BASE_URL}/api/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: text,
          provider: 'ollama',
          session_id: get().sessionId,
          sensor_data: sensorData,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No reader');

      const decoder = new TextDecoder();
      let fullText = '';
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith('data: ')) continue;

          try {
            const data = JSON.parse(trimmed.slice(6));
            // Handle generated event (media file)
            if (data.type === 'generated' && data.result) {
              const result = data.result;
              const file = result.file || result.path || '';
              const mediaUrl = result.media_url || '';
              const mediaType = result.media_type || '';
              if (file || mediaUrl) {
                // Update the assistant message with media info
                set((s) => ({
                  messages: s.messages.map((m) =>
                    m.id === assistantId ? { ...m, mediaUrl: mediaUrl || `/output/${file.split('/').pop()}`, mediaType } : m
                  ),
                }));
              }
            }
            if (data.token) {
              fullText += data.token;
              set((s) => ({
                messages: s.messages.map((m) =>
                  m.id === assistantId ? { ...m, content: fullText } : m
                ),
              }));
            }
            if (data.done) {
              const mediaUrl = data.media_url || '';
              const mediaType = data.media_type || '';
              set((s) => ({
                messages: s.messages.map((m) =>
                  m.id === assistantId ? { ...m, streaming: false, content: fullText || 'No response', mediaUrl: m.mediaUrl || mediaUrl, mediaType: m.mediaType || mediaType } : m
                ),
                isLoading: false,
              }));
              return;
            }
          } catch {
            continue;
          }
        }
      }

      // Fallback if stream ends without done
      set((s) => ({
        messages: s.messages.map((m) =>
          m.id === assistantId ? { ...m, streaming: false, content: fullText || 'No response' } : m
        ),
        isLoading: false,
      }));
    } catch (err: any) {
      // Fallback to non-streaming
      try {
        const { chatAPI } = await import('@/lib/api');
        const res = await chatAPI.send(text, get().sessionId);
        const data = res.data;
        set((s) => ({
          messages: s.messages.map((m) =>
            m.id === assistantId
              ? { ...m, content: data.response || data.error || 'No response', streaming: false }
              : m
          ),
          isLoading: false,
        }));
      } catch {
        set((s) => ({
          messages: s.messages.map((m) =>
            m.id === assistantId
              ? { ...m, content: '⚠️ Connection error. Check your network.', streaming: false }
              : m
          ),
          isLoading: false,
        }));
      }
    }
  },

  clearMessages: () => {
    const fresh = 'mobile_' + Date.now();
    SecureStore.setItemAsync(SESSION_KEY, fresh).catch(() => {});
    set({ messages: [], sessionId: fresh });
  },
}));
