import { create } from 'zustand';
import { systemAPI } from '@/lib/api';

interface SystemStats {
  cpu_percent: number;
  memory_percent: number;
  memory_used_mb: number;
  memory_total_mb: number;
  disk_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
  uptime: string;
  ollama_status: boolean;
  active_provider: string;
}

interface SystemState {
  stats: SystemStats | null;
  isLoading: boolean;
  lastUpdate: number;
  fetchStats: () => Promise<void>;
}

export const useSystemStore = create<SystemState>((set) => ({
  stats: null,
  isLoading: true,
  lastUpdate: 0,

  fetchStats: async () => {
    try {
      const res = await systemAPI.stats();
      if (res.data) {
        set({ stats: res.data, isLoading: false, lastUpdate: Date.now() });
      }
    } catch {
      set({ isLoading: false });
    }
  },
}));
