import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/api/client';
import { ENDPOINTS } from '@/api/endpoints';
import type { PaginatedResponse } from '@/api/types';

// ─── Types ───────────────────────────────────────────────────────────────────

export type PIStatus = 'DRAFT' | 'SENT' | 'APPROVED' | 'PAYMENT_PENDING' | 'PAID';
export type PICurrency = 'USD' | 'INR';

export interface ProformaLineItem {
  id?: number;
  product_name: string;
  quantity: number;
  rate: number;
  amount: number;
}

export interface ProformaInvoice {
  id: number;
  pi_number: string;
  date: string;
  customer: number;
  customer_name?: string;
  currency: PICurrency;
  exchange_rate: number;
  payment_terms: string;
  expected_shipment_date: string;
  total_amount: number;
  status: PIStatus;
  line_items: ProformaLineItem[];
  created_by?: number;
  created_at?: string;
  updated_at?: string;
}

export interface ProformaListItem {
  id: number;
  pi_number: string;
  date: string;
  customer_name: string;
  total_amount: number;
  currency: PICurrency;
  status: PIStatus;
}

export interface ProformaPayment {
  id: number;
  amount: number;
  payment_mode: string;
  payment_date: string;
  reference_number: string;
  notes: string;
  created_at: string;
}

export interface LinkedBooking {
  id: number;
  job_number: string;
  status: string;
  booking_date: string;
}

export interface CreateProformaPayload {
  date: string;
  customer: number;
  currency: PICurrency;
  exchange_rate: number;
  payment_terms: string;
  expected_shipment_date: string;
  line_items: Omit<ProformaLineItem, 'id'>[];
}

export interface UpdateProformaPayload extends Partial<CreateProformaPayload> {}

export interface ChangeStatusPayload {
  status: PIStatus;
}

// ─── Query Keys ──────────────────────────────────────────────────────────────

export const proformaKeys = {
  all: ['proforma-invoices'] as const,
  lists: () => [...proformaKeys.all, 'list'] as const,
  list: (params: Record<string, unknown>) => [...proformaKeys.lists(), params] as const,
  details: () => [...proformaKeys.all, 'detail'] as const,
  detail: (id: number) => [...proformaKeys.details(), id] as const,
};

// ─── Hooks ───────────────────────────────────────────────────────────────────

interface UseProformaListParams {
  page?: number;
  pageSize?: number;
  status?: PIStatus | '';
}

/**
 * Fetches paginated list of proforma invoices with optional status filter.
 */
export function useProformaList(params: UseProformaListParams = {}) {
  const { page = 1, pageSize = 25, status } = params;

  return useQuery<PaginatedResponse<ProformaListItem>>({
    queryKey: proformaKeys.list({ page, pageSize, status }),
    queryFn: async () => {
      const queryParams: Record<string, string | number> = {
        page,
        page_size: pageSize,
      };
      if (status) {
        queryParams.status = status;
      }
      const response = await apiClient.get(ENDPOINTS.PROFORMA_INVOICES, {
        params: queryParams,
      });
      return response.data;
    },
  });
}

/**
 * Fetches a single proforma invoice with full details.
 */
export function useProformaDetail(id: number | null) {
  return useQuery<ProformaInvoice>({
    queryKey: proformaKeys.detail(id!),
    queryFn: async () => {
      const response = await apiClient.get(ENDPOINTS.PROFORMA_INVOICE_DETAIL(id!));
      return response.data;
    },
    enabled: id !== null,
  });
}

/**
 * Creates a new proforma invoice.
 */
export function useCreateProforma() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CreateProformaPayload) => {
      const response = await apiClient.post(ENDPOINTS.PROFORMA_INVOICES, data);
      return response.data as ProformaInvoice;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: proformaKeys.all });
    },
  });
}

/**
 * Updates an existing proforma invoice.
 */
export function useUpdateProforma(id: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: UpdateProformaPayload) => {
      const response = await apiClient.patch(ENDPOINTS.PROFORMA_INVOICE_DETAIL(id), data);
      return response.data as ProformaInvoice;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: proformaKeys.all });
    },
  });
}

/**
 * Changes the status of a proforma invoice.
 */
export function useChangeProformaStatus(id: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: ChangeStatusPayload) => {
      const response = await apiClient.patch(ENDPOINTS.PROFORMA_INVOICE_STATUS(id), data);
      return response.data as ProformaInvoice;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: proformaKeys.all });
    },
  });
}

/**
 * Fetches payments for a specific proforma invoice.
 */
export function useProformaPayments(id: number | null) {
  return useQuery<ProformaPayment[]>({
    queryKey: ['proforma-payments', id],
    queryFn: async () => {
      const response = await apiClient.get(ENDPOINTS.PROFORMA_INVOICE_PAYMENTS(id!));
      const data = response.data;
      return Array.isArray(data) ? data : data.results ?? [];
    },
    enabled: id !== null,
  });
}

/**
 * Fetches bookings linked to a proforma invoice.
 */
export function useProformaBookings(id: number | null) {
  return useQuery<LinkedBooking[]>({
    queryKey: ['proforma-bookings', id],
    queryFn: async () => {
      const response = await apiClient.get(ENDPOINTS.PROFORMA_INVOICE_BOOKINGS(id!));
      const data = response.data;
      return Array.isArray(data) ? data : data.results ?? [];
    },
    enabled: id !== null,
  });
}
