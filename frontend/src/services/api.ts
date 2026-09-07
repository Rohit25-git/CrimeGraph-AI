import axios from 'axios';

// Set base URL. When running Vite dev server with proxy, this points to Vite dev server domain
const API_URL = '';

const api = axios.create({
  baseURL: API_URL,
});

// Interceptor to inject JWT token in headers
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

export const authAPI = {
  login: async (username: string, password: string) => {
    // OAuth2PasswordRequestForm expects URL encoded fields
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);
    const res = await api.post('/api/auth/login', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });
    localStorage.setItem('token', res.data.access_token);
    return res.data;
  },
  register: async (userData: { username: string; password: string; role?: string }) => {
    const res = await api.post('/api/auth/register', userData);
    return res.data;
  },
  getDemoPersonas: async () => {
    const res = await api.get('/api/auth/demo-personas');
    return res.data;
  },
  me: async () => {
    const res = await api.get('/api/auth/me');
    return res.data;
  },
  logout: () => {
    localStorage.removeItem('token');
  }
};

export const entitiesAPI = {
  getList: async (params?: { q?: string; type?: string; limit?: number; offset?: number }) => {
    const res = await api.get('/api/entities', { params });
    return res.data;
  },
  get: async (id: string) => {
    const res = await api.get(`/api/entities/${id}`);
    return res.data;
  },
  getConnections: async (id: string, depth = 1) => {
    const res = await api.get(`/api/entities/${id}/connections`, { params: { depth } });
    return res.data;
  },
  getEvidence: async (id: string) => {
    const res = await api.get(`/api/entities/${id}/evidence`);
    return res.data;
  }
};

export const relationshipsAPI = {
  getList: async (params?: { source?: string; target?: string; type?: string }) => {
    const res = await api.get('/api/relationships', { params });
    return res.data;
  },
  getEvidence: async (id: string) => {
    const res = await api.get(`/api/relationships/${id}/evidence`);
    return res.data;
  }
};

export const graphAPI = {
  getFull: async () => {
    const res = await api.get('/api/graph');
    return res.data;
  },
  getShortestPath: async (source: string, target: string, investigationId?: string, scope?: string) => {
    const params: any = { source, target };
    if (investigationId) params.investigation_id = investigationId;
    if (scope) params.scope = scope;
    const res = await api.get('/api/graph/shortest-path', { params });
    return res.data;
  }
};

export const analyticsAPI = {
  getCentrality: async () => {
    const res = await api.get('/api/analytics/centrality');
    return res.data;
  },
  getCommunities: async () => {
    const res = await api.get('/api/analytics/communities');
    return res.data;
  },
  getBridges: async () => {
    const res = await api.get('/api/analytics/bridges');
    return res.data;
  },
  getHealth: async () => {
    const res = await api.get('/api/analytics/health');
    return res.data;
  },
  getDataQuality: async () => {
    const res = await api.get('/api/analytics/data-quality');
    return res.data;
  }
};

export const investigationsAPI = {
  getList: async () => {
    const res = await api.get('/api/investigations');
    return res.data;
  },
  get: async (id: string) => {
    const res = await api.get(`/api/investigations/${id}`);
    return res.data;
  },
  getNetwork: async (id: string, scope = 'case') => {
    const res = await api.get(`/api/investigations/${id}/network`, { params: { scope } });
    return res.data;
  },
  create: async (data: any) => {
    const res = await api.post('/api/investigations', data);
    return res.data;
  },
  update: async (id: string, data: any) => {
    const res = await api.put(`/api/investigations/${id}`, data);
    return res.data;
  },
  delete: async (id: string) => {
    const res = await api.delete(`/api/investigations/${id}`);
    return res.data;
  }
};

export const resolutionsAPI = {
  getList: async () => {
    const res = await api.get('/api/resolutions');
    return res.data;
  },
  process: async (id: number, merge: boolean) => {
    const res = await api.post(`/api/resolutions/${id}`, { merge });
    return res.data;
  }
};

export const alertsAPI = {
  getList: async (params?: { severity?: string; status?: string }) => {
    const res = await api.get('/api/alerts', { params });
    return res.data;
  },
  updateStatus: async (id: number, status: string) => {
    const res = await api.patch(`/api/alerts/${id}`, { status });
    return res.data;
  },
  retrigger: async () => {
    const res = await api.post('/api/alerts/retrigger-detection');
    return res.data;
  }
};

export const assistantAPI = {
  ask: async (question: string, contextEntityId?: string) => {
    const res = await api.post('/api/assistant', { question, context_entity_id: contextEntityId });
    return res.data;
  }
};

export const reportsAPI = {
  generate: async (investigationName: string, selectedEntityIds: string[]) => {
    const res = await api.post('/api/reports', { investigation_name: investigationName, selected_entity_ids: selectedEntityIds });
    return res.data;
  }
};

export const uploadAPI = {
  uploadFile: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await api.post('/api/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return res.data;
  }
};

export default api;

export const mlAPI = {
  getRiskScores: async () => {
    const res = await api.get('/ml/risk');
    return res.data;
  },

  getEntityRisk: async (entityId: string) => {
    const res = await api.get(`/ml/risk/${entityId}`);
    return res.data;
  }
};

