/**
 * Phase 12.8.1 — Mobile Axios Networking Client
 * Includes JWT authorization interceptors and offline error handling.
 */

import axios from 'axios';
import { store, logout } from '../store';

const API_BASE_URL = 'https://api.analystos.enterprise.com';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Attach JWT Bearer Token
apiClient.interceptors.request.use(
  (config) => {
    const state = store.getState();
    const token = state.auth.accessToken;
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: Handle 401 Unauthorized / Token Expiry
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response && error.response.status === 401) {
      // Clear credentials on authentication expiry
      store.dispatch(logout());
    }
    return Promise.reject(error);
  }
);
