/**
 * Shared API response types used across the frontend.
 */

/** Standard Django REST Framework paginated response shape. */
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/** Field-level validation errors returned by DRF on 400 responses. */
export interface ValidationErrorResponse {
  [field: string]: string[];
}

/** Non-field-level error (e.g. authentication failure). */
export interface DetailErrorResponse {
  detail: string;
}

/** Union type covering common API error shapes. */
export type ApiErrorResponse = ValidationErrorResponse | DetailErrorResponse;

/** Token pair returned by the login endpoint. */
export interface TokenPair {
  access: string;
  refresh: string;
}

/** Response from the token refresh endpoint. */
export interface TokenRefreshResponse {
  access: string;
}
