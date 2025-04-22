import { create } from 'zustand';
import { apiClient } from './api';

export interface ChatMessage {
  id: string;
  message_id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  feedback?: {
    is_positive: boolean;
    comment?: string;
  };
}

interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  isSendingFeedback: boolean;
  sendMessage: (sessionId: string, message: string) => Promise<void>;
  clearHistory: (sessionId: string) => Promise<void>;
  fetchHistory: (sessionId: string) => Promise<void>;
  submitFeedback: (sessionId: string, messageId: string, isPositive: boolean, comment?: string) => Promise<void>;
}

export const useChat = create<ChatState>((set) => ({
  messages: [],
  isLoading: false,
  error: null,
  isSendingFeedback: false,

  sendMessage: async (sessionId, message) => {
    try {
      set({ isLoading: true, error: null });
      const response = await apiClient.chat.sendMessage(sessionId, message);
      set((state) => ({
        messages: [...state.messages, response],
      }));
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Failed to send message' });
    } finally {
      set({ isLoading: false });
    }
  },

  clearHistory: async (sessionId) => {
    try {
      set({ isLoading: true, error: null });
      await apiClient.chat.clearHistory(sessionId);
      set({ messages: [] });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Failed to clear chat history' });
    } finally {
      set({ isLoading: false });
    }
  },

  fetchHistory: async (sessionId) => {
    try {
      set({ isLoading: true, error: null });
      const messages = await apiClient.chat.getHistory(sessionId);
      set({ messages });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Failed to fetch chat history' });
    } finally {
      set({ isLoading: false });
    }
  },
  
  submitFeedback: async (sessionId, messageId, isPositive, comment) => {
    try {
      set({ isSendingFeedback: true, error: null });
      const response = await apiClient.chat.submitFeedback(sessionId, messageId, isPositive, comment);
      
      // Update the message with feedback information
      set((state) => ({
        messages: state.messages.map((msg) => 
          msg.id === messageId || msg.message_id === messageId
            ? { ...msg, feedback: { is_positive: isPositive, comment } }
            : msg
        )
      }));
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Failed to submit feedback' });
    } finally {
      set({ isSendingFeedback: false });
    }
  }
})); 