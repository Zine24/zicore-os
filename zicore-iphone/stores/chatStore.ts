import { create } from 'zustand';
import { BASE_URL } from '@/lib/api';
import { authStorage } from '@/lib/auth';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  streaming?: boolean;
}

interface ChatState {
  messages: Message[];
  isLoading: boolean;
  sessionId: string;

  sendMessage: (text: string) => Promise<void>;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isLoading: false,
  sessionId: 'iphone_' + Date.now(),

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
            if (data.token) {
              fullText += data.token;
              set((s) => ({
                messages: s.messages.map((m) =>
                  m.id === assistantId ? { ...m, content: fullText } : m
                ),
              }));
            }
            if (data.done) {
              set((s) => ({
                messages: s.messages.map((m) =>
                  m.id === assistantId ? { ...m, streaming: false, content: fullText || 'No response' } : m
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

      set((s) => ({
        messages: s.messages.map((m) =>
          m.id === assistantId ? { ...m, streaming: false, content: fullText || 'No response' } : m
        ),
        isLoading: false,
      }));
    } catch (err: any) {
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
              ? { ...m, content: 'Connection error. Check your network.', streaming: false }
              : m
          ),
          isLoading: false,
        }));
      }
    }
  },

  clearMessages: () => set({ messages: [], sessionId: 'iphone_' + Date.now() }),
}));
