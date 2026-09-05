import axios from 'axios';

// Default to relative path for Vite proxy or production serving
const baseURL = import.meta.env.VITE_API_URL || '';

export const apiClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to inject the JWT token if available, plus default X-API-Key fallback
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    // Include test-api-key fallback for endpoints requiring API key
    config.headers['X-API-Key'] = 'test-api-key';
    return config;
  },
  (error) => Promise.reject(error)
);

// Global response interceptor for handling 401s and other standard errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // If we get a 401 Unauthorized, we should clear the token and force re-login
      if (error.response.status === 401) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user_role');
        // Dispatch custom event so React can catch it and route to login
        window.dispatchEvent(new Event('auth:unauthorized'));
      }
    }
    return Promise.reject(error);
  }
);
