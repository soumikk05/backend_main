import { apiClient } from './client';

export const operationsApi = {
  /**
   * Verify the full audit hash chain.
   */
  getAuditIntegrity: async () => {
    const response = await apiClient.get('/api/audit/integrity');
    return response.data;
  },

  /**
   * Get audit log for a specific screening.
   */
  getAuditLog: async (screeningId) => {
    const response = await apiClient.get(`/api/audit/${screeningId}`);
    return response.data;
  },

  /**
   * Get the chronological timeline for a specific screening.
   */
  getTimeline: async (screeningId) => {
    const response = await apiClient.get(`/api/timeline/${screeningId}`);
    return response.data;
  },

  /**
   * Get processing metrics for a specific screening.
   */
  getMetrics: async (screeningId) => {
    const response = await apiClient.get(`/api/metrics/${screeningId}`);
    return response.data;
  },

  /**
   * Get the localized anomaly heatmap data.
   */
  getHeatmap: async (screeningId) => {
    const response = await apiClient.get(`/api/heatmap/${screeningId}`);
    return response.data;
  },

  /**
   * Get the full dashboard hydration payload.
   */
  getDashboard: async (screeningId) => {
    const response = await apiClient.get(`/api/dashboard/${screeningId}`);
    return response.data;
  }
};
