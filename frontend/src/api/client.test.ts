import { describe, it, expect, beforeEach } from 'vitest';
import fc from 'fast-check';
import type { InternalAxiosRequestConfig } from 'axios';
import { AxiosHeaders } from 'axios';
import { setTokens, clearTokens } from '@/auth/tokenStore';
import apiClient from './client';

// Feature: react-frontend, Property 1: Bearer Token Attachment Invariant
// **Validates: Requirements 1.4**

/**
 * Get the request interceptor's fulfilled handler from the Axios instance.
 * Axios stores interceptors internally in a handlers array.
 */
function getRequestInterceptor(): (
  config: InternalAxiosRequestConfig,
) => InternalAxiosRequestConfig {
  const interceptors = apiClient.interceptors.request as unknown as {
    handlers: Array<{
      fulfilled: (config: InternalAxiosRequestConfig) => InternalAxiosRequestConfig;
    }>;
  };
  return interceptors.handlers[0]!.fulfilled;
}

describe('Property 1: Bearer Token Attachment Invariant', () => {
  beforeEach(() => {
    clearTokens();
  });

  it('attaches Bearer token header when token is present in store', () => {
    const interceptor = getRequestInterceptor();

    fc.assert(
      fc.property(
        fc.constantFrom('get', 'post', 'put', 'patch', 'delete'),
        fc.stringMatching(/^\/[a-z0-9/]*$/),
        fc.oneof(
          fc.constant(undefined),
          fc.dictionary(
            fc.string({ minLength: 1, maxLength: 10 }),
            fc.string({ minLength: 1, maxLength: 20 }),
          ),
        ),
        fc.string({ minLength: 1, maxLength: 64 }),
        (method, urlPath, body, token) => {
          // Set the token in the store
          setTokens(token, 'refresh-token');

          const headers = new AxiosHeaders();
          const config: InternalAxiosRequestConfig = {
            method,
            url: urlPath,
            data: body,
            headers,
          };

          const result = interceptor(config);

          expect(result.headers.Authorization).toBe(`Bearer ${token}`);
        },
      ),
      { numRuns: 100 },
    );
  });

  it('does NOT attach Bearer token header when no token is present', () => {
    const interceptor = getRequestInterceptor();

    fc.assert(
      fc.property(
        fc.constantFrom('get', 'post', 'put', 'patch', 'delete'),
        fc.stringMatching(/^\/[a-z0-9/]*$/),
        (method, urlPath) => {
          // Ensure no token is set
          clearTokens();

          const headers = new AxiosHeaders();
          const config: InternalAxiosRequestConfig = {
            method,
            url: urlPath,
            headers,
          };

          const result = interceptor(config);

          expect(result.headers.Authorization).toBeUndefined();
        },
      ),
      { numRuns: 100 },
    );
  });
});
