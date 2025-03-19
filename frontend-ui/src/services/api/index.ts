import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { QRAuthResponse, SessionVerifyResponse, DialogListResponse, SessionStatus, Response, ResponseListResponse, ResponseUpdateRequest, MessageListResponse, MessageFetchOptions, ResponseGenerateRequest, ResponseWithDialog, DialogSelectionResponse } from '../../types';

// Create a base API instance
const apiClient: AxiosInstance = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for authentication
apiClient.interceptors.request.use(
  (config) => {
    // Only add token if available and if Authorization header isn't already set
    if (!config.headers.Authorization) {
      const token = localStorage.getItem('accessToken');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Add response interceptor for token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // Special case: verifySession endpoint should not trigger refresh to avoid loops
    if (originalRequest.url?.includes('/auth/session/verify')) {
      return Promise.reject(error);
    }
    
    // If error is 401 and we haven't tried to refresh the token yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        // Try to refresh the token
        const refreshToken = localStorage.getItem('refreshToken');
        if (!refreshToken) {
          throw new Error('No refresh token available');
        }
        
        const response = await axios.post(
          `${apiClient.defaults.baseURL}/auth/refresh`,
          { refresh_token: refreshToken }
        );
        
        const { access_token } = response.data;
        localStorage.setItem('accessToken', access_token);
        
        // Retry the original request with the new token
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        // If refresh fails, clear tokens and reject
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

// Generic API request function
const apiRequest = async <T>(config: AxiosRequestConfig): Promise<T> => {
  try {
    // Add request logging for auth endpoints
    if (config.url?.includes('/auth/')) {
      console.log(`[API Debug] Request to ${config.url}`, config);
    }
    
    const response: AxiosResponse<T> = await apiClient(config);
    
    // Add response logging for auth endpoints
    if (config.url?.includes('/auth/')) {
      console.log(`[API Debug] Response from ${config.url}:`, response.data);
    }
    
    return response.data;
  } catch (error) {
    console.error('API request failed:', error);
    
    // Add more detailed error logging
    if (axios.isAxiosError(error)) {
      console.error(`[API Error] ${config.method?.toUpperCase()} ${config.url} failed with status ${error.response?.status}`);
      
      if (error.response?.data) {
        console.error('[API Error] Response data:', error.response.data);
      }
      
      if (error.response?.status === 401) {
        console.error('[API Error] Authentication error - token may be invalid or expired');
        console.error('[API Error] Authorization header:', error.config?.headers?.Authorization || 'Not set');
      }
    }
    
    throw error;
  }
};

// Types for config endpoints
export interface ModelParameter {
  id: string;
  name: string;
  description: string;
  min?: number;
  max?: number;
  default: number | string;
  step?: number;
  options?: string[];
  models?: string[];
}

export interface Model {
  id: string;
  name: string;
  context_length: number;
  description: string;
}

export interface Provider {
  name: string;
  description: string;
  models: Model[];
  default_model: string;
  parameters: ModelParameter[];
  special_parameters?: ModelParameter[];
}

export interface ProviderModels {
  providers: Record<string, Provider>;
}

export interface ProviderSettings {
  model: string;
  temperature: number;
  max_tokens: number;
  [key: string]: number | string;
}

export interface ModelSettings {
  active_provider: string;
  providers: Record<string, ProviderSettings>;
}

// API endpoints
export const api = {
  // Auth endpoints
  auth: {
    login: (data: { username: string; password: string }) => 
      apiRequest({
        method: 'POST',
        url: '/auth/login',
        data,
      }),
    refresh: (refreshToken: string) => 
      apiRequest({
        method: 'POST',
        url: '/auth/refresh',
        data: { refresh_token: refreshToken },
      }),
    createQRAuth: () => 
      apiRequest<QRAuthResponse>({
        method: 'POST',
        url: '/auth/qr',
      }),
    verifySession: async () => {
      try {
        // Get the token from localStorage
        const token = localStorage.getItem('accessToken');
        // Even without a token, we can call the endpoint 
        // as it will return UNAUTHENTICATED status
        
        // Make the request
        const response = await apiRequest<SessionVerifyResponse>({
          method: 'GET',
          url: '/auth/session/verify',
          headers: token ? {
            Authorization: `Bearer ${token}`
          } : {}
        });
        
        // If authenticated, store tokens
        if (response.status === SessionStatus.AUTHENTICATED && response.access_token) {
          localStorage.setItem('accessToken', response.access_token);
          if (response.refresh_token) {
            localStorage.setItem('refreshToken', response.refresh_token);
          }
        }
        
        return response;
      } catch (error) {
        console.error('[API Debug] Session verification failed:', error);
        throw error;
      }
    },
    logout: () => 
      apiRequest<{ status: string }>({
        method: 'POST',
        url: '/auth/logout',
      }),
    devLogin: (telegram_id: number) => 
      apiRequest<{ 
        session_id: string; 
        token?: string;  // Backend returns this format
        access_token?: string; 
        refresh_token?: string;
        expires_at: string;
      }>({
        method: 'POST',
        url: '/auth/dev-login',
        data: { telegram_id },
      }),
    // Phone auth - first step to send the code
    initiatePhoneAuth: (phoneNumber: string) => 
      apiRequest<{ session_id: string; expires_at: string; phone_code_hash: string }>({
        method: 'POST',
        url: '/auth/phone',
        data: { phone_number: phoneNumber },
      }),
    // Phone auth - verify the code
    verifyPhoneCode: (phoneNumber: string, code: string, sessionId: string) => 
      apiRequest<SessionVerifyResponse>({
        method: 'POST',
        url: '/auth/phone/verify',
        data: { 
          phone_number: phoneNumber,
          code: code,
          session_id: sessionId
        },
      }),
  },
  
  // Dialog endpoints
  dialogs: {
    getAll: () => 
      apiRequest({
        method: 'GET',
        url: '/dialogs',
      }),
    getByTelegramId: (telegramId: string) =>
      apiRequest<DialogSelectionResponse>({
        method: 'GET',
        url: `/dialogs/by-telegram-id/${telegramId}`,
      }),
    update: (id: number, data: { 
      is_processing_enabled?: boolean; 
      auto_send_enabled?: boolean;
    }) => 
      apiRequest({
        method: 'PATCH',
        url: `/dialogs/${String(id)}`,
        data,
      }),
    delete: (id: number) => 
      apiRequest({
        method: 'DELETE',
        url: `/dialogs/${String(id)}`,
      }),
    select: (dialogId: number, dialogName: string) => 
      apiRequest({
        method: 'POST',
        url: '/dialogs/select',
        data: {
          dialog_id: String(dialogId),
          dialog_name: dialogName,
          is_processing_enabled: true,
          auto_send_enabled: false
        },
      }),
    unselect: (dialogId: number) => 
      apiRequest({
        method: 'DELETE',
        url: `/dialogs/selected/${String(dialogId)}`,
      }),
    getSelected: () => 
      apiRequest({
        method: 'GET',
        url: '/dialogs/selected',
      }),
  },
  
  // Telegram Dialogs
  telegram: {
    getDialogs: async () => {
      // Check if user is authenticated
      const token = localStorage.getItem('accessToken');
      if (!token) {
        // Return a specific error that indicates authentication is required
        throw new Error('AUTH_REQUIRED');
      }
      
      // If authenticated, proceed with the API request
      return apiRequest<DialogListResponse>({
        method: 'GET',
        url: '/messages/dialogs',
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
    },
  },
  
  // Message endpoints
  messages: {
    getByDialogId: (dialogId: string, options?: MessageFetchOptions) => 
      apiRequest<MessageListResponse>({
        method: 'GET',
        url: `/messages/dialog/${dialogId}`,
        params: options
      }),
  },
  
  // Response endpoints
  responses: {
    getPending: (skip: number = 0, limit: number = 10) => 
      apiRequest<ResponseListResponse>({
        method: 'GET',
        url: `/responses/pending?skip=${skip}&limit=${limit}`,
      }),
    
    getHistory: (skip: number = 0, limit: number = 10, statusFilter?: string) => {
      let url = `/responses/history?skip=${skip}&limit=${limit}`;
      if (statusFilter && statusFilter !== 'all') {
        url += `&status_filter=${statusFilter}`;
      }
      return apiRequest<ResponseListResponse>({
        method: 'GET',
        url,
      });
    },
    
    getById: (responseId: string) => 
      apiRequest<Response>({
        method: 'GET',
        url: `/responses/${responseId}`,
      }),
    
    update: (responseId: string, data: ResponseUpdateRequest) => 
      apiRequest<Response>({
        method: 'PUT',
        url: `/responses/${responseId}`,
        data,
      }),
    
    approve: (responseId: string) => 
      apiRequest<Response>({
        method: 'POST',
        url: `/responses/${responseId}/approve`,
      }),
    
    reject: (responseId: string) => 
      apiRequest<Response>({
        method: 'POST',
        url: `/responses/${responseId}/reject`,
      }),
    
    send: (responseId: string) => 
      apiRequest<Response>({
        method: 'POST',
        url: `/responses/${responseId}/send`,
      }),
    
    generate: {
      private: (dialog_id: string) =>
        apiRequest<ResponseWithDialog>({
          method: 'POST',
          url: '/responses/generate/private',
          data: { telegram_dialog_id: dialog_id }
        }),
      group: (dialog_id: string) =>
        apiRequest<ResponseWithDialog>({
          method: 'POST',
          url: '/responses/generate/group',
          data: { telegram_dialog_id: dialog_id }
        })
    },
  },
  
  // Settings endpoints
  settings: {
    getModels: () => 
      apiRequest({
        method: 'GET',
        url: '/settings/models',
      }),
    updateModel: (data: { model_name: string; system_prompt: string }) => 
      apiRequest({
        method: 'PUT',
        url: '/settings/models',
        data,
      }),
    getProfile: () => 
      apiRequest({
        method: 'GET',
        url: '/settings/profile',
      }),
    updateProfile: (data: { [key: string]: string | number | boolean }) => 
      apiRequest({
        method: 'PUT',
        url: '/settings/profile',
        data,
      }),
  },

  // Config endpoints
  config: {
    getProviderModels: () => 
      apiRequest<ProviderModels>({
        method: 'GET',
        url: '/config/providers',
      }),

    getModelSettings: () => 
      apiRequest<ModelSettings>({
        method: 'GET',
        url: '/config/settings',
      }),

    updateModelSettings: (settings: Partial<ModelSettings>) => 
      apiRequest<ModelSettings>({
        method: 'PATCH',
        url: '/config/settings',
        data: settings,
      }),

    validateApiKey: (provider: string) => 
      apiRequest<{ valid: boolean; message?: string }>({
        method: 'POST',
        url: '/config/validate-key',
        data: { provider },
      }),
  },
};

export default api; 