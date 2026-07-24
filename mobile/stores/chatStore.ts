import { create } from 'zustand';
import { chatAPI } from '@/lib/api';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
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
  sessionId: 'mobile_' + Date.now(),

  sendMessage: async (text: string) => {
    const userMsg: Message = {
      id: 'u_' + Date.now(),
      role: 'user',
      content: text,
      timestamp: Date.now(),
    };
    set((s) => ({ messages: [...s.messages, userMsg], isLoading: true }));

    try {
      const res = await chatAPI.send(text, get().sessionId);
      const data = res.data;
      const assistantMsg: Message = {
        id: 'a_' + Date.now(),
        role: 'assistant',
        content: data.response || data.error || 'No response',
        timestamp: Date.now(),
      };
      set((s) => ({ messages: [...s.messages, assistantMsg], isLoading: false }));
    } catch (err: any) {
      const errorMsg: Message = {
        id: 'e_' + Date.now(),
        role: 'assistant',
        content: '⚠️ Connection error. Check your network.',
        timestamp: Date.now(),
      };
      set((s) => ({ messages: [...s.messages, errorMsg], isLoading: false }));
    }
  },

  clearMessages: () => set({ messages: [], sessionId: 'mobile_' + Date.now() }),
}));
