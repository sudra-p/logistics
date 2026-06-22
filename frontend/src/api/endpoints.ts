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
  // Proforma Invoices
  PROFORMA_INVOICES: 'proforma-invoices/',
  PROFORMA_INVOICE_DETAIL: (id: number) => `proforma-invoices/${id}/`,
  PROFORMA_INVOICE_STATUS: (id: number) => `proforma-invoices/${id}/status/`,
  PROFORMA_INVOICE_BOOKINGS: (id: number) => `proforma-invoices/${id}/bookings/`,
  PROFORMA_INVOICE_PAYMENTS: (id: number) => `proforma-invoices/${id}/payments/`,

  // Payments
  PAYMENTS: 'payments/',
  PAYMENT_DETAIL: (id: number) => `payments/${id}/`,

  // Stock Items / Inventory
  STOCK_ITEMS: 'stock-items/',
  STOCK_ITEM_DETAIL: (id: number) => `stock-items/${id}/`,

  // Commercial Invoices
  BOOKING_COMMERCIAL_INVOICE: (bookingId: number) => `bookings/${bookingId}/commercial-invoice/`,
  COMMERCIAL_INVOICE_DETAIL: (id: number) => `commercial-invoices/${id}/`,
  COMMERCIAL_INVOICE_FINALIZE: (id: number) => `commercial-invoices/${id}/finalize/`,

  // Packing Lists
  BOOKING_PACKING_LIST: (bookingId: number) => `bookings/${bookingId}/packing-list/`,
  PACKING_LIST_DETAIL: (id: number) => `packing-lists/${id}/`,
  PACKING_LIST_FINALIZE: (id: number) => `packing-lists/${id}/finalize/`,

  // Bill of Lading
  BOOKING_BL: (bookingId: number) => `bookings/${bookingId}/bl/`,
  BL_DETAIL: (id: number) => `bl/${id}/`,
  BL_STATUS: (id: number) => `bl/${id}/status/`,

  // Dashboard
  DASHBOARD_KPIS: 'dashboard/kpis/',
  DASHBOARD_PROFORMA_STATUS: 'dashboard/proforma-status/',
  DASHBOARD_READY_FOR_BOOKING: 'dashboard/ready-for-booking/',
  DASHBOARD_CURRENT_SHIPMENTS: 'dashboard/current-shipments/',
  DASHBOARD_DOCUMENT_STATUS: 'dashboard/document-status/',
  DASHBOARD_ALERTS: 'dashboard/alerts/',

  // Operations
  OPERATIONS: 'operations/',

  // Container Stuffing
  CONTAINER_STUFF: (bookingId: number, containerId: number) =>
    `bookings/${bookingId}/containers/${containerId}/stuff/`,
} as const;
