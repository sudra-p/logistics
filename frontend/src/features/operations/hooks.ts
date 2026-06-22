import { useQuery } from '@tanstack/react-query';
import apiClient from '@/api/client';
import { ENDPOINTS } from '@/api/endpoints';

// ─── Types ───────────────────────────────────────────────────────────────────

export interface OperationsRecord {
  id: number;
  pi_number: string;
  booking_number: string;
  consignee: string;
  shipping_line: string;
  container_type: string;
  vessel_name: string;
  voyage: string;
  pol: string;
  pod: string;
  fpd: string;
  etd: string | null;
  eta: string | null;
  forwarder: string;
  status: string;
}

export interface OperationsFilters {
  customer?: string;
  shipping_line?: string;
  status?: string;
  etd_from?: string;
  etd_to?: string;
  pol?: string;
}

export interface OperationsParams {
  page: number;
  pageSize: number;
  filters: OperationsFilters;
  sortField?: string;
  sortDirection?: 'asc' | 'desc';
}

export interface OperationsResponse {
  count: number;
  results: OperationsRecord[];
}

// ─── Query Keys ──────────────────────────────────────────────────────────────

export const operationsKeys = {
  all: ['operations'] as const,
  list: (params: OperationsParams) => [...operationsKeys.all, params] as const,
};

// ─── Hooks ───────────────────────────────────────────────────────────────────

export function useOperationsView(params: OperationsParams) {
  return useQuery<OperationsResponse>({
    queryKey: operationsKeys.list(params),
    queryFn: async () => {
      const queryParams: Record<string, string> = {
        page: String(params.page),
        page_size: String(params.pageSize),
      };

      if (params.filters.customer) queryParams.customer = params.filters.customer;
      if (params.filters.shipping_line) queryParams.shipping_line = params.filters.shipping_line;
      if (params.filters.status) queryParams.status = params.filters.status;
      if (params.filters.etd_from) queryParams.etd_from = params.filters.etd_from;
      if (params.filters.etd_to) queryParams.etd_to = params.filters.etd_to;
      if (params.filters.pol) queryParams.pol = params.filters.pol;

      if (params.sortField) {
        const ordering = params.sortDirection === 'desc' ? `-${params.sortField}` : params.sortField;
        queryParams.ordering = ordering;
      }

      const response = await apiClient.get(ENDPOINTS.OPERATIONS, { params: queryParams });
      return response.data;
    },
    staleTime: 30_000,
  });
}
