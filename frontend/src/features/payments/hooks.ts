import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/api/client';
import { ENDPOINTS } from '@/api/endpoints';
import type { PaginatedResponse } from '@/api/types';

// ─── Types ───────────────────────────────────────────────────────────────────

export type PaymentMode = 'BANK' | 'CASH' | 'LC';

export interface Payment {
  id: number;
  proforma_invoice: number;
  pi_number: string;
  customer_name: string;
  amount: number;
  payment_mode: PaymentMode;
  payment_date: string;
  reference_number: string;
  notes: string;
  created_by?: number;
  created_at?: string;
}

export interface PaymentListItem {
  id: number;
  pi_number: string;
  customer_name: string;
  amount: number;
  payment_mode: PaymentMode;
  payment_date: string;
  reference_number: string;
}

export interface CreatePaymentPayload {
  proforma_invoice: number;
  amount: number;
  payment_mode: PaymentMode;
  payment_date: string;
  reference_number?: string;
  notes?: string;
}

export interface ProformaPaymentSummary {
  id: number;
  pi_number: string;
  customer_name: string;
  total_amount: number;
  total_paid: number;
  outstanding_balance: number;
}

// ─── Query Keys ──────────────────────────────────────────────────────────────

export const paymentKeys = {
  all: ['payments'] as const,
  lists: () => [...paymentKeys.all, 'list'] as const,
  list: (params: Record<string, unknown>) => [...paymentKeys.lists(), params] as const,
};

// ─── Hooks ───────────────────────────────────────────────────────────────────

interface UsePaymentListParams {
  page?: number;
  pageSize?: number;
}

/**
 * Fetches paginated list of payments.
 */
export function usePaymentList(params: UsePaymentListParams = {}) {
  const { page = 1, pageSize = 25 } = params;

  return useQuery<PaginatedResponse<PaymentListItem>>({
    queryKey: paymentKeys.list({ page, pageSize }),
    queryFn: async () => {
      const queryParams: Record<string, string | number> = {
        page,
        page_size: pageSize,
      };
      const response = await apiClient.get(ENDPOINTS.PAYMENTS, {
        params: queryParams,
      });
      return response.data;
    },
  });
}

/**
 * Creates a new payment.
 */
export function useCreatePayment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CreatePaymentPayload) => {
      const response = await apiClient.post(ENDPOINTS.PAYMENTS, data);
      return response.data as Payment;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: paymentKeys.all });
      void queryClient.invalidateQueries({ queryKey: ['proforma-invoices'] });
    },
  });
}

/**
 * Fetches payment summary for a specific proforma invoice (customer name, total, outstanding).
 */
export function useProformaPayments(piId: number | null) {
  return useQuery<ProformaPaymentSummary>({
    queryKey: ['proforma-payment-summary', piId],
    queryFn: async () => {
      const response = await apiClient.get(ENDPOINTS.PROFORMA_INVOICE_PAYMENTS(piId!));
      const payments = Array.isArray(response.data) ? response.data : response.data.results ?? [];
      // Also fetch the PI detail
      const piResponse = await apiClient.get(ENDPOINTS.PROFORMA_INVOICE_DETAIL(piId!));
      const pi = piResponse.data;
      const totalPaid = payments.reduce((sum: number, p: { amount: number }) => sum + Number(p.amount), 0);
      return {
        id: pi.id,
        pi_number: pi.pi_number,
        customer_name: pi.customer_name ?? '',
        total_amount: Number(pi.total_amount),
        total_paid: totalPaid,
        outstanding_balance: Number(pi.total_amount) - totalPaid,
      };
    },
    enabled: piId !== null,
  });
}
