import { apiClient } from './client';

export const historyApi = {
  /**
   * Fetch a list of historical screenings.
   * @param {Object} params - optional query params: skip, limit, sort_by
   */
  getHistory: async (params = { skip: 0, limit: 100 }) => {
    const response = await apiClient.get('/api/history', { params });
    return response.data;
  },

  /**
   * Fetch a specific screening record.
   */
  getRecord: async (recordId) => {
    const response = await apiClient.get(`/api/history/${recordId}`);
    return response.data;
  },

  /**
   * Get the current blacklist.
   */
  getBlacklist: async () => {
    const response = await apiClient.get('/api/registry/blacklist');
    return response.data;
  },

  /**
   * Add a document to the blacklist.
   * @param {Object} data - { document_number, reason }
   */
  addToBlacklist: async (data) => {
    const response = await apiClient.post('/api/registry/blacklist', data);
    return response.data;
  },

  /**
   * Remove a document from the blacklist.
   */
  removeFromBlacklist: async (documentNumber) => {
    const response = await apiClient.delete(`/api/registry/blacklist/${documentNumber}`);
    return response.data;
  }
};
