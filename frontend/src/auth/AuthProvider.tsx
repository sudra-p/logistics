import { createContext, useState, useCallback, useMemo, useEffect, type ReactNode } from 'react';
import axios from 'axios';
import type { AuthContextValue, User } from './types';
import apiClient from '@/api/client';
import { ENDPOINTS } from '@/api/endpoints';
import { setTokens, clearTokens, getRefreshToken } from './tokenStore';
import type { TokenPair, TokenRefreshResponse } from '@/api/types';

export const AuthContext = createContext<AuthContextValue | null>(null);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isRestoring, setIsRestoring] = useState(true);

  // On mount: try to restore session from persisted refresh token
  useEffect(() => {
    const restoreSession = async () => {
      const refreshToken = getRefreshToken();
      if (!refreshToken) {
        setIsRestoring(false);
        return;
      }

      try {
        // Get a new access token using the refresh token
        const { data } = await axios.post<TokenRefreshResponse>(
          '/api/accounts/token/refresh/',
          { refresh: refreshToken },
        );

        // Store the new access token (keep the same refresh token)
        setTokens(data.access, refreshToken);

        // Fetch user profile
        const { data: profile } = await apiClient.get<User>(ENDPOINTS.USER_PROFILE);
        setUser(profile);
      } catch {
        // Refresh token is expired or invalid — clear and stay logged out
        clearTokens();
      } finally {
        setIsRestoring(false);
      }
    };

    void restoreSession();
  }, []);

  const login = useCallback(async (username: string, password: string): Promise<void> => {
    const { data: tokens } = await apiClient.post<TokenPair>(ENDPOINTS.TOKEN, {
      username,
      password,
    });

    setTokens(tokens.access, tokens.refresh);

    const { data: profile } = await apiClient.get<User>(ENDPOINTS.USER_PROFILE);
    setUser(profile);
  }, []);

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
    window.location.href = '/login';
  }, []);

  const refreshUser = useCallback(async () => {
    const { data: profile } = await apiClient.get<User>(ENDPOINTS.USER_PROFILE);
    setUser(profile);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: user !== null,
      login,
      logout,
      refreshUser,
      role: user?.role ?? null,
    }),
    [user, login, logout, refreshUser],
  );

  // Show nothing while restoring session (prevents flash of login page)
  if (isRestoring) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-3 border-primary/30 border-t-primary rounded-full animate-spin" />
      </div>
    );
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
