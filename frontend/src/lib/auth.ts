import { create } from 'zustand';
import { apiClient } from './api';
import { baseURL } from './api';

export interface User {
  id: number;
  username: string;
  email: string;
  preferences: UserPreferences;
}

export interface UserPreferences {
  study_days: string[];
  hours_per_day: number;
  difficulty_level: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<User>;
  register: (username: string, password: string, email?: string) => Promise<User>;
  logout: () => void;
  updatePreferences: (preferences: UserPreferences) => Promise<any>;
  checkAuth: () => Promise<void>;
}

export const useAuth = create<AuthState>((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  login: async (username: string, password: string) => {
    try {
      set({ isLoading: true, error: null });
      console.log('Starting login process for user:', username);
      
      const response = await apiClient.auth.login(username, password);
      console.log('Login response received:', response);
      
      if (!response.access_token) {
        console.error('No access token in response:', response);
        throw new Error('No access token received from server');
      }
      
      // Create a user object from the response
      const user = {
        id: response.user?.id?.toString() || '1',
        username: response.user?.username || username,
        email: response.user?.email,
        preferences: response.user?.preferences || {}
      };
      
      console.log('Created user object:', user);
      
      // Store token and update state
      localStorage.setItem('token', response.access_token);
      console.log('Token stored in localStorage');
      
      set({ user, isAuthenticated: true, isLoading: false });
      console.log('Auth state updated:', { user, isAuthenticated: true });
      
      return user;
    } catch (error) {
      console.error('Login error:', error);
      set({ 
        error: error instanceof Error ? error.message : 'Login failed',
        isLoading: false 
      });
      throw error;
    }
  },

  register: async (username: string, password: string, email?: string) => {
    try {
      set({ isLoading: true, error: null });
      console.log('Registering user:', { username, email });
      
      // Log the registration URL using the imported baseURL
      console.log('Registration URL:', `${baseURL}/api/v1/auth/register`);
      
      const response = await apiClient.auth.register(username, password, email);
      console.log('Registration response:', response);
      
      // Create a user object from the response
      const user = {
        id: response.id?.toString() || '1',
        username: response.username || username,
        email: response.email || email,
        preferences: response.preferences || {}
      };
      
      // Store token and update state
      if (response.access_token) {
        localStorage.setItem('token', response.access_token);
      } else {
        console.warn('No access token in registration response');
      }
      set({ user, isAuthenticated: true, isLoading: false });
      
      return user; // Return the user object
    } catch (error) {
      console.error('Registration error:', error);
      set({ 
        error: error instanceof Error ? error.message : 'Registration failed',
        isLoading: false 
      });
      throw error; // Re-throw the error so it can be caught by the onSubmit handler
    }
  },

  logout: () => {
    localStorage.removeItem('token');
    set({ user: null, isAuthenticated: false });
  },

  updatePreferences: async (preferences: UserPreferences) => {
    try {
      console.log('Auth store: Starting preferences update');
      console.log('Auth store: Current state:', get());
      set({ isLoading: true, error: null });
      console.log('Auth store: Making API call with preferences:', preferences);
      const response = await apiClient.auth.updatePreferences(preferences);
      console.log('Auth store: API response received:', response);
      
      // Update the user state with the new preferences
      set((state) => {
        console.log('Auth store: Updating state with new preferences');
        console.log('Auth store: Previous state:', state);
        const newState = {
          user: state.user ? {
            ...state.user,
            preferences: response.preferences || preferences
          } : null,
          isLoading: false,
          error: null
        };
        console.log('Auth store: New state:', newState);
        return newState;
      });
      
      return response;
    } catch (error) {
      console.error('Auth store: Error updating preferences:', error);
      set({ 
        error: error instanceof Error ? error.message : 'Failed to update preferences',
        isLoading: false 
      });
      throw error;
    }
  },

  checkAuth: async () => {
    const state = get();
    if (state.isLoading || (state.isAuthenticated && state.user)) return;
    
    try {
      set({ isLoading: true, error: null });
      const token = localStorage.getItem('token');
      if (!token) {
        set({ isAuthenticated: false, user: null, isLoading: false });
        return;
      }
      
      console.log('Checking auth with token:', token);
      const response = await apiClient.auth.me();
      
      // Create a user object from the response
      const user = {
        id: response.id?.toString() || '1',
        username: response.username || 'unknown',
        email: response.email || '',
        preferences: response.preferences || {}
      };
      
      set({ user, isAuthenticated: true, isLoading: false });
    } catch (error) {
      console.error('Auth check error:', error);
      localStorage.removeItem('token');
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  }
})); 