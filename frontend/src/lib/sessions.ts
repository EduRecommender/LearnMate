import { create } from 'zustand';
import { apiClient } from './api';

export interface StudySession {
  id: string;
  name: string;
  field_of_study: string;
  study_goal: string;
  context: string;
  time_commitment: number;
  difficulty_level: string;
  progress: number | Record<string, any>;
  created_at: string;
  updated_at: string;
  preferences: Record<string, any>;
  syllabus: Record<string, any>;
  resources?: Array<{
    id: string;
    name: string;
    url: string;
    type: string;
  }>;
}

interface SessionsState {
  sessions: StudySession[];
  currentSession: string | null;
  isLoading: boolean;
  error: string | null;
  fetchSessions: () => Promise<void>;
  createSession: (data: Omit<StudySession, 'id' | 'created_at' | 'updated_at'>) => Promise<void>;
  updateSession: (id: string, data: Partial<StudySession>) => Promise<void>;
  deleteSession: (id: string) => Promise<void>;
  setCurrentSession: (id: string | null) => void;
}

export const useSessions = create<SessionsState>((set, get) => ({
  sessions: [],
  currentSession: null,
  isLoading: false,
  error: null,

  fetchSessions: async () => {
    set({ isLoading: true, error: null });
    try {
      const sessions = await apiClient.sessions.list();
      set({ sessions, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch sessions',
        isLoading: false,
      });
    }
  },

  createSession: async (data) => {
    set({ isLoading: true, error: null });
    try {
      const session = await apiClient.sessions.create(data);
      set((state) => ({
        sessions: [...state.sessions, session],
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to create session',
        isLoading: false,
      });
      throw error;
    }
  },

  updateSession: async (id, data) => {
    set({ isLoading: true, error: null });
    try {
      const session = await apiClient.sessions.update(id, data);
      set((state) => ({
        sessions: state.sessions.map((s) => (s.id === id ? session : s)),
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to update session',
        isLoading: false,
      });
      throw error;
    }
  },

  deleteSession: async (id) => {
    set({ isLoading: true, error: null });
    try {
      await apiClient.sessions.delete(id);
      set((state) => ({
        sessions: state.sessions.filter((s) => s.id !== id),
        currentSession: state.currentSession === id ? null : state.currentSession,
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to delete session',
        isLoading: false,
      });
      throw error;
    }
  },

  setCurrentSession: (id) => {
    set({ currentSession: id });
  },
})); 