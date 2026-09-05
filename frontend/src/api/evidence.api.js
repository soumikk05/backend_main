import { apiClient } from './client';

export const evidenceApi = {
  /**
   * Generates a URL for downloading evidence. The caller must attach the token manually or use the client.
   * Since this returns a file, it's often easier to fetch it as a blob.
   */
  downloadEvidence: async (screeningId, filename) => {
    const response = await apiClient.get(`/evidence/${screeningId}/${filename}`, {
      responseType: 'blob'
    });
    return response.data;
  },

  /**
   * Admin only: Purges expired evidence.
   */
  purgeEvidence: async () => {
    const response = await apiClient.post('/api/privacy/purge');
    return response.data;
  }
};
