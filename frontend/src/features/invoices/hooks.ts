import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/api/client';
import { ENDPOINTS } from '@/api/endpoints';

// ─── Types ───────────────────────────────────────────────────────────────────

export type DocumentStatus = 'DRAFT' | 'FINALIZED';

export interface CommercialInvoiceLineItem {
  id?: number;
  product_name: string;
  quantity: number;
  rate: number;
  amount: number;
  net_weight: number | null;
  gross_weight: number | null;
  hs_code: string;
  num_packages: number | null;
}

export interface CommercialInvoice {
  id: number;
  booking: number;
  invoice_number: string;
  revision: number;
  status: DocumentStatus;
  line_items: CommercialInvoiceLineItem[];
  created_by?: number;
  created_at?: string;
  updated_at?: string;
}

export interface PackingListLineItem {
  id?: number;
  product_name: string;
  quantity: number;
  num_packages: number;
  net_weight: number;
  gross_weight: number;
  package_type: string;
}

export interface PackingList {
  id: number;
  booking: number;
  packing_list_number: string;
  revision: number;
  status: DocumentStatus;
  line_items: PackingListLineItem[];
  created_by?: number;
  created_at?: string;
  updated_at?: string;
}

export interface DocumentRevision {
  revision: number;
  status: DocumentStatus;
  created_at: string;
  created_by_name?: string;
}

export interface CreateCommercialInvoicePayload {
  line_items: Omit<CommercialInvoiceLineItem, 'id'>[];
}

export interface UpdateCommercialInvoicePayload {
  line_items?: Omit<CommercialInvoiceLineItem, 'id'>[];
}

export interface CreatePackingListPayload {
  line_items: Omit<PackingListLineItem, 'id'>[];
}

export interface UpdatePackingListPayload {
  line_items?: Omit<PackingListLineItem, 'id'>[];
}

// ─── Query Keys ──────────────────────────────────────────────────────────────

export const invoiceKeys = {
  all: ['commercial-invoices'] as const,
  detail: (bookingId: number) => [...invoiceKeys.all, 'detail', bookingId] as const,
};

export const packingListKeys = {
  all: ['packing-lists'] as const,
  detail: (bookingId: number) => [...packingListKeys.all, 'detail', bookingId] as const,
};

// ─── Commercial Invoice Hooks ────────────────────────────────────────────────

/**
 * Fetches the commercial invoice for a booking.
 */
export function useCommercialInvoice(bookingId: number | null) {
  return useQuery<CommercialInvoice>({
    queryKey: invoiceKeys.detail(bookingId!),
    queryFn: async () => {
      const response = await apiClient.get(ENDPOINTS.BOOKING_COMMERCIAL_INVOICE(bookingId!));
      return response.data;
    },
    enabled: bookingId !== null,
    retry: false,
  });
}

/**
 * Creates a new commercial invoice for a booking (auto-filled from PI).
 */
export function useCreateInvoice(bookingId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CreateCommercialInvoicePayload) => {
      const response = await apiClient.post(
        ENDPOINTS.BOOKING_COMMERCIAL_INVOICE(bookingId),
        data
      );
      return response.data as CommercialInvoice;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: invoiceKeys.all });
    },
  });
}

/**
 * Updates a commercial invoice.
 */
export function useUpdateInvoice(invoiceId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: UpdateCommercialInvoicePayload) => {
      const response = await apiClient.patch(
        ENDPOINTS.COMMERCIAL_INVOICE_DETAIL(invoiceId),
        data
      );
      return response.data as CommercialInvoice;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: invoiceKeys.all });
    },
  });
}

/**
 * Finalizes a commercial invoice (locks it from further edits).
 */
export function useFinalizeInvoice(invoiceId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.patch(
        ENDPOINTS.COMMERCIAL_INVOICE_FINALIZE(invoiceId)
      );
      return response.data as CommercialInvoice;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: invoiceKeys.all });
    },
  });
}

// ─── Packing List Hooks ──────────────────────────────────────────────────────

/**
 * Fetches the packing list for a booking.
 */
export function usePackingList(bookingId: number | null) {
  return useQuery<PackingList>({
    queryKey: packingListKeys.detail(bookingId!),
    queryFn: async () => {
      const response = await apiClient.get(ENDPOINTS.BOOKING_PACKING_LIST(bookingId!));
      return response.data;
    },
    enabled: bookingId !== null,
    retry: false,
  });
}

/**
 * Creates a new packing list for a booking (auto-filled from PI).
 */
export function useCreatePackingList(bookingId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CreatePackingListPayload) => {
      const response = await apiClient.post(
        ENDPOINTS.BOOKING_PACKING_LIST(bookingId),
        data
      );
      return response.data as PackingList;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: packingListKeys.all });
    },
  });
}

/**
 * Updates a packing list.
 */
export function useUpdatePackingList(packingListId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: UpdatePackingListPayload) => {
      const response = await apiClient.patch(
        ENDPOINTS.PACKING_LIST_DETAIL(packingListId),
        data
      );
      return response.data as PackingList;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: packingListKeys.all });
    },
  });
}

/**
 * Finalizes a packing list (locks it from further edits).
 */
export function useFinalizePackingList(packingListId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.patch(
        ENDPOINTS.PACKING_LIST_FINALIZE(packingListId)
      );
      return response.data as PackingList;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: packingListKeys.all });
    },
  });
}
