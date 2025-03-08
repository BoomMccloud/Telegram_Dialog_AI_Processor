import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';

// Create a base API instance
const apiClient: AxiosInstance = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for authentication
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
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
        // If refresh fails, clear tokens and redirect to login
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        // In a real app, you might want to redirect to login page here
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

// Generic API request function
const apiRequest = async <T>(config: AxiosRequestConfig): Promise<T> => {
  try {
    const response: AxiosResponse<T> = await apiClient(config);
    return response.data;
  } catch (error) {
    console.error('API request failed:', error);
    throw error;
  }
};

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
    logout: () => 
      apiRequest({
        method: 'POST',
        url: '/auth/logout',
      }),
  },
  
  // Dialog endpoints
  dialogs: {
    getAll: () => 
      apiRequest({
        method: 'GET',
        url: '/dialogs',
      }),
    update: (id: number, data: { is_processing_enabled?: boolean; auto_send_enabled?: boolean }) => 
      apiRequest({
        method: 'PATCH',
        url: `/dialogs/${id}`,
        data,
      }),
    delete: (id: number) => 
      apiRequest({
        method: 'DELETE',
        url: `/dialogs/${id}`,
      }),
  },
  
  // Response endpoints
  responses: {
    getPending: () => 
      apiRequest({
        method: 'GET',
        url: '/responses/pending',
      }),
    approve: (id: number) => 
      apiRequest({
        method: 'POST',
        url: `/responses/${id}/approve`,
      }),
    reject: (id: number) => 
      apiRequest({
        method: 'POST',
        url: `/responses/${id}/reject`,
      }),
    update: (id: number, data: { edited_response: string }) => 
      apiRequest({
        method: 'PUT',
        url: `/responses/${id}`,
        data,
      }),
    getHistory: () => 
      apiRequest({
        method: 'GET',
        url: '/responses/history',
      }),
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
};

export default api; 