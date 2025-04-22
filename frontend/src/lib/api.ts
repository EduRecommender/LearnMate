import axios from 'axios';
import { User, UserPreferences } from './auth';

export const baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002';

// Create axios instance with extended timeouts and retries
const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
  // Set a very long default timeout (2 hours) for all requests
  timeout: 7200000, // 2 hours in milliseconds
  timeoutErrorMessage: 'Request timed out - the server took too long to respond',
});

// Add request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    console.error('Request error:', error);
    return Promise.reject(error);
  }
);

// Retry logic
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error;
    
    // Log detailed error information
    console.error('API Error:', {
      url: config?.url,
      method: config?.method,
      status: response?.status,
      statusText: response?.statusText,
      data: response?.data,
      error: error.message
    });
    
    // Only retry on network errors, timeouts, or 5xx server errors
    if ((!response || error.code === 'ECONNABORTED' || response.status >= 500) && 
        config && 
        !config._retry && 
        !config.url.includes('/auth/me')) {
      config._retry = true;
      try {
        // Wait 1 second before retrying
        await new Promise(resolve => setTimeout(resolve, 1000));
        return await api(config);
      } catch (retryError) {
        return Promise.reject(retryError);
      }
    }

    if (error.response?.status === 401) {
      // Don't redirect if we're already on the login page or checking auth
      if (!window.location.pathname.includes('/auth/') && !config.url.includes('/auth/me')) {
        localStorage.removeItem('token');
        window.location.href = '/auth/login';
      }
      return Promise.reject(new Error('Authentication required'));
    }

    if (error.code === 'ECONNABORTED') {
      console.error('Request timeout:', error);
      
      // Special handling for chat endpoint timeouts
      if (config.url.includes('/chat')) {
        return Promise.reject(new Error('The system is taking longer than expected to process your request. This may be due to the complexity of your query or server load. You can continue waiting or try a simpler request.'));
      }
      
      return Promise.reject(new Error(error.message || 'Request timed out - please check if the server is running'));
    }

    if (!error.response) {
      console.error('Network error:', error);
      return Promise.reject(new Error('Network error - please check if the backend server is running at ' + baseURL));
    }

    return Promise.reject(error);
  }
);

export const apiClient = {
  auth: {
    login: async (username: string, password: string) => {
      console.log('Making login request to:', `${baseURL}/api/v1/auth/login`);
      try {
        const response = await api.post('/api/v1/auth/login', { username, password });
        console.log('Login response:', response.data);
        if (response.data.access_token) {
          localStorage.setItem('token', response.data.access_token);
        }
        return response.data;
      } catch (error: any) {
        console.error('Login error:', error.response?.data || error.message);
        throw error;
      }
    },
    register: async (username: string, password: string, email?: string) => {
      // Validate username length
      if (username.length < 3 || username.length > 50) {
        throw new Error('Username must be between 3 and 50 characters');
      }

      // Validate password length
      if (password.length < 4) {
        throw new Error('Password must be at least 4 characters');
      }

      // Ensure email is null if it's an empty string
      const emailToSend = email === '' ? null : email;
      
      // Create the request payload that matches the UserCreate model exactly
      const payload = { 
        username, 
        password, 
        email: emailToSend,
        is_active: true,
        preferences: {}
      };
      
      // Log the data being sent (without sensitive info)
      console.log('Registering with:', { 
        ...payload,
        password: '********' // Don't log the actual password
      });
      
      console.log('Registration endpoint URL:', `${baseURL}/api/v1/auth/register`);
      
      try {
        // Send the request with the exact payload structure FastAPI expects
        console.log('Sending registration request...');
        const response = await api.post('/api/v1/auth/register', payload, {
          headers: {
            'Content-Type': 'application/json'
          }
        });
        
        // Log successful response
        console.log('Registration successful - Status:', response.status);
        console.log('Registration response data:', response.data);
        
        // If registration is successful, store the token
        if (response.data && response.data.access_token) {
          console.log('Storing access token in localStorage');
          localStorage.setItem('token', response.data.access_token);
        } else {
          console.warn('No access token in registration response');
        }
        
        return response.data;
      } catch (error: any) {
        // Log detailed error information
        console.error('Registration request failed');
        console.error('Error object:', error);
        console.error('Registration error details:', {
          status: error.response?.status,
          statusText: error.response?.statusText,
          data: error.response?.data,
          message: error.message,
          requestPayload: {
            ...payload,
            password: '********'
          }
        });
        
        if (error.response?.status === 422) {
          const errorDetail = error.response.data?.detail || 'Validation error';
          throw new Error(`Registration validation error: ${errorDetail}`);
        }
        
        // Re-throw the error with more context
        throw new Error(`Registration failed: ${error.response?.data?.detail || error.message}`);
      }
    },
    me: async () => {
      const response = await api.get('/api/v1/auth/me');
      return response.data;
    },
    updatePreferences: async (preferences: UserPreferences) => {
      console.log('API Client: Starting preferences update request');
      console.log('API Client: Request data:', preferences);
      try {
        const response = await api.put('/api/v1/auth/preferences', preferences);
        console.log('API Client: Response received:', response.data);
        return response.data;
      } catch (error: any) {
        console.error('API Client: Error in updatePreferences:', error);
        if (error.response) {
          console.error('API Client: Error response:', {
            status: error.response.status,
            data: error.response.data,
            headers: error.response.headers
          });
        }
        throw error;
      }
    },
  },
  sessions: {
    list: async () => {
      const response = await api.get('/api/v1/sessions/');
      return response.data;
    },
    create: async (data: any) => {
      console.log('Creating session with data:', data);
      try {
        const response = await api.post('/api/v1/sessions/', data);
        console.log('Session creation response:', response.data);
        return response.data;
      } catch (error: any) {
        console.error('Session creation error:', {
          status: error.response?.status,
          data: error.response?.data,
          message: error.message
        });
        throw error;
      }
    },
    get: async (id: string) => {
      const response = await api.get(`/api/v1/sessions/${id}`);
      return response.data;
    },
    update: async (id: string, data: any) => {
      const response = await api.put(`/api/v1/sessions/${id}`, data);
      return response.data;
    },
    delete: async (id: string) => {
      const response = await api.delete(`/api/v1/sessions/${id}`);
      return response.data;
    },
    uploadMaterial: async (sessionId: string, file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      console.log('Uploading file:', file.name, 'to session:', sessionId);
      try {
        const response = await api.post(`/api/v1/sessions/${sessionId}/resources`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
        console.log('Upload response:', response.data);
        return response.data;
      } catch (error: any) {
        console.error('Upload error:', error.response?.data || error.message);
        throw error;
      }
    },
    uploadSyllabus: async (sessionId: string, file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      console.log('Uploading syllabus:', file.name, 'to session:', sessionId);
      try {
        const response = await api.post(`/api/v1/sessions/${sessionId}/syllabus`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
        console.log('Upload response:', response.data);
        return response.data;
      } catch (error: any) {
        console.error('Upload error:', error.response?.data || error.message);
        throw error;
      }
    },
    deleteMaterial: async (sessionId: string, resourceId: string) => {
      const response = await api.delete(`/api/v1/sessions/${sessionId}/resources/${resourceId}`);
      return response.data;
    },
  },
  chat: {
    getHistory: async (sessionId: string) => {
      const response = await api.get(`/api/v1/sessions/${sessionId}/chat`);
      return response.data;
    },
    startMessageProcessing: async (sessionId: string, message: string) => {
      console.log('[API-DEBUG] Starting message processing for session', sessionId);
      try {
        const response = await api.post(`/api/v1/sessions/${sessionId}/chat/start`, { message });
        console.log('[API-DEBUG] Message processing started:', response.data);
        return response.data;
      } catch (error: any) {
        console.error('[API-DEBUG] Error starting message processing:', error);
        throw error;
      }
    },
    checkMessageStatus: async (sessionId: string, requestId: string) => {
      console.log('[API-DEBUG] Checking message status for request', requestId, 'in session', sessionId);
      try {
        // Add a cache-busting parameter to ensure we always get a fresh response
        const timestamp = new Date().getTime();
        const response = await api.get(`/api/v1/sessions/${sessionId}/chat/status/${requestId}?_=${timestamp}`);
        console.log('[API-DEBUG] Message status response:', response.data);
        
        // Handle the case where the request is complete but result is missing
        if (response.data.status === 'complete' && !response.data.result) {
          console.warn('[API-DEBUG] Status is complete but result is missing, will re-fetch');
          // Try one more time with an additional delay
          await new Promise(resolve => setTimeout(resolve, 1000));
          const retryResponse = await api.get(`/api/v1/sessions/${sessionId}/chat/status/${requestId}?_=${timestamp+1000}`);
          console.log('[API-DEBUG] Retry message status response:', retryResponse.data);
          return retryResponse.data;
        }
        
        return response.data;
      } catch (error: any) {
        console.error('[API-DEBUG] Error checking message status:', error);
        throw error;
      }
    },
    sendMessage: async (sessionId: string, message: string) => {
      const response = await api.post(`/api/v1/sessions/${sessionId}/chat`, { message });
      return response.data;
    },
    clearHistory: async (sessionId: string) => {
      try {
        const response = await api.delete(`/api/v1/sessions/${sessionId}/chat`);
        return response.data;
      } catch (error: any) {
        console.error('[DEBUG] Error clearing chat history:', error);
        throw error;
      }
    },
    submitFeedback: async (sessionId: string, messageId: string, isPositive: boolean, comment?: string) => {
      try {
        console.log(`[API-DEBUG] Submitting ${isPositive ? 'positive' : 'negative'} feedback for message ${messageId}`);
        const response = await api.post(`/api/v1/sessions/${sessionId}/chat/${messageId}/feedback`, {
          message_id: messageId,
          is_positive: isPositive,
          comment: comment || null
        });
        console.log('[API-DEBUG] Feedback submission response:', response.data);
        return response.data;
      } catch (error: any) {
        console.error('[API-DEBUG] Error submitting feedback:', error);
        throw error;
      }
    },
  },
};

export default apiClient;