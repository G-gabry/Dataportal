import axios from 'axios';
import type {
  Source,
  DiscoveredURL,
  Item,
  ScrapeJob,
  PaginatedResponse,
  LoginRequest,
  Token,
  AIConfig,
  User,
} from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Auth
export const auth = {
  login: async (data: LoginRequest): Promise<Token> => {
    const response = await api.post('/api/v1/auth/login', data);
    return response.data;
  },
  me: async (): Promise<User> => {
    const response = await api.get('/api/v1/auth/me');
    return response.data;
  },
};

// Sources
export const sources = {
  list: async (params?: {
    page?: number;
    page_size?: number;
    type?: string;
    is_active?: boolean;
    is_important?: boolean;
    search?: string;
  }): Promise<PaginatedResponse<Source>> => {
    const response = await api.get('/api/v1/sources', { params });
    return response.data;
  },
  get: async (id: string): Promise<Source> => {
    const response = await api.get(`/api/v1/sources/${id}`);
    return response.data;
  },
  create: async (data: Partial<Source>): Promise<Source> => {
    const response = await api.post('/api/v1/sources', data);
    return response.data;
  },
  update: async (id: string, data: Partial<Source>): Promise<Source> => {
    const response = await api.put(`/api/v1/sources/${id}`, data);
    return response.data;
  },
  delete: async (id: string): Promise<void> => {
    await api.delete(`/api/v1/sources/${id}`);
  },
  scrape: async (id: string, jobType = 'FULL_SCRAPE'): Promise<{ message: string }> => {
    const response = await api.post(`/api/v1/sources/${id}/scrape`, null, {
      params: { job_type: jobType },
    });
    return response.data;
  },
};

// URLs
export const urls = {
  list: async (params?: {
    page?: number;
    page_size?: number;
    source_id?: string;
    status?: string;
    relevance?: string;
    priority?: string;
    human_verified?: boolean;
    search?: string;
  }): Promise<PaginatedResponse<DiscoveredURL>> => {
    const response = await api.get('/api/v1/urls', { params });
    return response.data;
  },
  get: async (id: string): Promise<DiscoveredURL> => {
    const response = await api.get(`/api/v1/urls/${id}`);
    return response.data;
  },
  update: async (id: string, data: Partial<DiscoveredURL>): Promise<DiscoveredURL> => {
    const response = await api.put(`/api/v1/urls/${id}`, data);
    return response.data;
  },
  verify: async (id: string): Promise<DiscoveredURL> => {
    const response = await api.post(`/api/v1/urls/${id}/verify`);
    return response.data;
  },
  stats: async (sourceId?: string): Promise<any> => {
    const response = await api.get('/api/v1/urls/stats/summary', {
      params: { source_id: sourceId },
    });
    return response.data;
  },
};

// Items
export const items = {
  list: async (params?: {
    page?: number;
    page_size?: number;
    source_id?: string;
    item_type?: string;
    status?: string;
    human_verified?: boolean;
    needs_review?: boolean;
    search?: string;
  }): Promise<PaginatedResponse<Item>> => {
    const response = await api.get('/api/v1/items', { params });
    return response.data;
  },
  reviewQueue: async (params?: {
    page?: number;
    page_size?: number;
    item_type?: string;
  }): Promise<PaginatedResponse<Item>> => {
    const response = await api.get('/api/v1/items/review-queue', { params });
    return response.data;
  },
  get: async (id: string): Promise<Item> => {
    const response = await api.get(`/api/v1/items/${id}`);
    return response.data;
  },
  create: async (data: Partial<Item>): Promise<Item> => {
    const response = await api.post('/api/v1/items', data);
    return response.data;
  },
  update: async (id: string, data: Partial<Item>): Promise<Item> => {
    const response = await api.put(`/api/v1/items/${id}`, data);
    return response.data;
  },
  delete: async (id: string): Promise<void> => {
    await api.delete(`/api/v1/items/${id}`);
  },
  verify: async (id: string): Promise<Item> => {
    const response = await api.post(`/api/v1/items/${id}/verify`);
    return response.data;
  },
  publish: async (id: string): Promise<Item> => {
    const response = await api.post(`/api/v1/items/${id}/publish`);
    return response.data;
  },
  stats: async (sourceId?: string): Promise<any> => {
    const response = await api.get('/api/v1/items/stats/summary', {
      params: { source_id: sourceId },
    });
    return response.data;
  },
};

// Jobs
export const jobs = {
  list: async (params?: {
    page?: number;
    page_size?: number;
    source_id?: string;
    status?: string;
  }): Promise<PaginatedResponse<ScrapeJob>> => {
    const response = await api.get('/api/v1/jobs', { params });
    return response.data;
  },
  get: async (id: string): Promise<ScrapeJob> => {
    const response = await api.get(`/api/v1/jobs/${id}`);
    return response.data;
  },
  cancel: async (id: string): Promise<{ message: string }> => {
    const response = await api.post(`/api/v1/jobs/${id}/cancel`);
    return response.data;
  },
  logs: async (id: string, params?: { page?: number; page_size?: number }): Promise<any> => {
    const response = await api.get(`/api/v1/jobs/${id}/logs`, { params });
    return response.data;
  },
  stats: async (): Promise<any> => {
    const response = await api.get('/api/v1/jobs/stats/summary');
    return response.data;
  },
};

// Settings
export const settings = {
  getAIConfig: async (): Promise<AIConfig> => {
    const response = await api.get('/api/v1/settings/ai-config');
    return response.data;
  },
  updateAIConfig: async (data: Partial<AIConfig>): Promise<AIConfig> => {
    const response = await api.put('/api/v1/settings/ai-config', data);
    return response.data;
  },
  getAvailableModels: async (): Promise<{ models: { provider: string; model: string; is_default: boolean }[] }> => {
    const response = await api.get('/api/v1/settings/available-models');
    return response.data;
  },
};

// Schemas
export const schemas = {
  list: async (): Promise<any[]> => {
    const response = await api.get('/api/v1/schemas');
    return response.data;
  },
  get: async (itemType: string): Promise<any> => {
    const response = await api.get(`/api/v1/schemas/${itemType}`);
    return response.data;
  },
  update: async (itemType: string, data: any): Promise<any> => {
    const response = await api.put(`/api/v1/schemas/${itemType}`, data);
    return response.data;
  },
};

export default api;
