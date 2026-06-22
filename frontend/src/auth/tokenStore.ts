// Token store with in-memory access token and persisted refresh token.
// Access token stays in memory only (short-lived, 60min).
// Refresh token is stored in localStorage to survive page refreshes.

const REFRESH_TOKEN_KEY = 'logistics_refresh_token';

let accessToken: string | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(access: string, refresh: string): void {
  accessToken = access;
  localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
}

export function clearTokens(): void {
  accessToken = null;
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}
