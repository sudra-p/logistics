import { describe, it, expect, beforeEach } from 'vitest';
import * as fc from 'fast-check';
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from './tokenStore';

describe('tokenStore', () => {
  beforeEach(() => {
    clearTokens();
  });

  describe('unit tests', () => {
    it('returns null for access token when no tokens are set', () => {
      expect(getAccessToken()).toBeNull();
    });

    it('returns null for refresh token when no tokens are set', () => {
      expect(getRefreshToken()).toBeNull();
    });

    it('stores and retrieves access token', () => {
      setTokens('access-123', 'refresh-456');
      expect(getAccessToken()).toBe('access-123');
    });

    it('stores and retrieves refresh token', () => {
      setTokens('access-123', 'refresh-456');
      expect(getRefreshToken()).toBe('refresh-456');
    });

    it('overwrites previous tokens when setTokens is called again', () => {
      setTokens('first-access', 'first-refresh');
      setTokens('second-access', 'second-refresh');
      expect(getAccessToken()).toBe('second-access');
      expect(getRefreshToken()).toBe('second-refresh');
    });

    it('clears both tokens', () => {
      setTokens('access-123', 'refresh-456');
      clearTokens();
      expect(getAccessToken()).toBeNull();
      expect(getRefreshToken()).toBeNull();
    });
  });

  // Feature: react-frontend, Property 2: Token Storage Exclusion
  describe('Property 2: Token Storage Exclusion', () => {
    /**
     * **Validates: Requirements 1.8**
     *
     * For any token string value, after calling setTokens(access, refresh),
     * neither localStorage nor sessionStorage SHALL contain that token value in any key.
     */
    it('tokens are never stored in localStorage or sessionStorage', () => {
      fc.assert(
        fc.property(
          fc.string({ minLength: 1 }),
          fc.string({ minLength: 1 }),
          (access, refresh) => {
            setTokens(access, refresh);

            // Check localStorage does not contain either token value
            for (let i = 0; i < localStorage.length; i++) {
              const key = localStorage.key(i)!;
              const value = localStorage.getItem(key);
              expect(value).not.toBe(access);
              expect(value).not.toBe(refresh);
            }

            // Check sessionStorage does not contain either token value
            for (let i = 0; i < sessionStorage.length; i++) {
              const key = sessionStorage.key(i)!;
              const value = sessionStorage.getItem(key);
              expect(value).not.toBe(access);
              expect(value).not.toBe(refresh);
            }

            // Tokens are correctly stored in memory
            expect(getAccessToken()).toBe(access);
            expect(getRefreshToken()).toBe(refresh);

            // Clean up for next iteration
            clearTokens();
          }
        ),
        { numRuns: 100 }
      );
    });
  });
});
