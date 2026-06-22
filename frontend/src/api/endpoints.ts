/**
 * API endpoint path constants.
 * All paths are relative to the Axios baseURL (`/api/`).
 */

// Auth
export const ENDPOINTS = {
  // Authentication
  TOKEN: 'accounts/token/',
  TOKEN_REFRESH: 'accounts/token/refresh/',
  USER_PROFILE: 'accounts/users/me/',
  USER_AVATAR: 'accounts/users/me/avatar/',

  // Bookings
  BOOKINGS: 'bookings/',
  BOOKING_DETAIL: (id: number) => `bookings/${id}/`,
  BOOKING_SEARCH: 'bookings/search/',
  BOOKING_CONTAINERS: (bookingId: number) => `bookings/${bookingId}/containers/`,
  BOOKING_CONTAINER_DETAIL: (bookingId: number, containerId: number) =>
    `bookings/${bookingId}/containers/${containerId}/`,
  BOOKING_TRANSHIPMENTS: (bookingId: number) => `bookings/${bookingId}/transhipments/`,
  BOOKING_TRANSHIPMENT_DETAIL: (bookingId: number, legId: number) =>
    `bookings/${bookingId}/transhipments/${legId}/`,

  // Master Data
  MASTER_DATA: (entityType: string) => `master-data/${entityType}/`,
  MASTER_DATA_DETAIL: (entityType: string, id: number) => `master-data/${entityType}/${id}/`,

  // Reports
  REPORT_PENDING_DO: 'reports/pending-do/',
  REPORT_MASTER: 'reports/master/',
  REPORT_EXPORT: (reportType: string) => `reports/${reportType}/export/`,
} as const;
