import { apiClient } from './client';

export const authApi = {
  /**
   * Authenticate a user and receive a JWT.
   * @param {string} username 
   * @param {string} password 
   * @param {string} role - one of: "officer", "supervisor", "admin", "auditor"
   * @returns {Promise<{access_token: string, token_type: string, role: string}>}
   */
  login: async (username, password, role) => {
    const response = await apiClient.post('/api/auth/token', {
      username,
      password,
      role
    });
    return response.data;
  }
};
