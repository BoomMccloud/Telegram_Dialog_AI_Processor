import { AxiosResponse } from 'axios';
import api from './api';

// Types from provider_models.json
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

// Types from model_settings.json
export interface ProviderSettings {
  model: string;
  temperature: number;
  max_tokens: number;
  [key: string]: number | string;  // For provider-specific parameters
}

export interface ModelSettings {
  active_provider: string;
  providers: Record<string, ProviderSettings>;
}

// API functions
export const modelApi = {
  getProviderModels: async (): Promise<ProviderModels> => {
    const response: AxiosResponse<ProviderModels> = await api.get('/config/providers');
    return response.data;
  },

  getModelSettings: async (): Promise<ModelSettings> => {
    const response: AxiosResponse<ModelSettings> = await api.get('/config/settings');
    return response.data;
  },

  updateModelSettings: async (settings: Partial<ModelSettings>): Promise<ModelSettings> => {
    const response: AxiosResponse<ModelSettings> = await api.patch('/config/settings', settings);
    return response.data;
  },

  validateApiKey: async (provider: string): Promise<{ valid: boolean; message?: string }> => {
    const response: AxiosResponse<{ valid: boolean; message?: string }> = 
      await api.post('/config/validate-key', { provider });
    return response.data;
  }
}; 