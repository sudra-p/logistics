import axios from 'axios';
import type { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from '@/auth/tokenStore';
import type { TokenRefreshResponse } from './types';

/**
 * Axios instance configured for the logistics ERP API.
 * BaseURL is `/api/` so all requests are proxied by Nginx to the Django backend.
 */
const apiClient = axios.create({
  baseURL: '/api/',
  headers: {
    'Content-Type': 'application/json',
  },
});

// ---------------------------------------------------------------------------
// Request interceptor: attach Bearer token
// ---------------------------------------------------------------------------

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: unknown) => Promise.reject(error),
);

// ---------------------------------------------------------------------------
// Response interceptor: handle 401 with token refresh + request queuing
// ---------------------------------------------------------------------------

/** Tracks whether a refresh is already in progress. */
let isRefreshing = false;

/** Queue of requests waiting for the refresh to complete. */
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

/**
 * Process all queued requests once the refresh resolves or rejects.
 */
function processQueue(error: unknown, token: string | null): void {
  for (const { resolve, reject } of failedQueue) {
    if (error) {
      reject(error);
    } else {
      resolve(token!);
    }
  }
  failedQueue = [];
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // Only handle 401s, and only attempt refresh once per request
    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    // If a refresh is already in flight, queue this request
    if (isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then((token) => {
        originalRequest.headers.Authorization = `Bearer ${token}`;
        return apiClient(originalRequest);
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    const refreshToken = getRefreshToken();

    if (!refreshToken) {
      // No refresh token available — fail immediately
      isRefreshing = false;
      processQueue(error, null);
      clearTokens();
      window.location.href = '/login';
      return Promise.reject(error);
    }

    try {
      // Attempt token refresh using a raw axios call (not apiClient) to avoid interceptor loops
      const { data } = await axios.post<TokenRefreshResponse>(
        '/api/accounts/token/refresh/',
        { refresh: refreshToken },
      );

      const newAccessToken = data.access;
      setTokens(newAccessToken, refreshToken);

      // Resolve all queued requests with the new token
      processQueue(null, newAccessToken);

      // Retry the original request with the new token
      originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
      return apiClient(originalRequest);
    } catch (refreshError) {
      // Refresh failed — reject all queued requests, clear tokens, redirect to login
      processQueue(refreshError, null);
      clearTokens();
      window.location.href = '/login';
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  },
);

export default apiClient;
