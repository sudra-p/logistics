import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/api/client';
import { ENDPOINTS } from '@/api/endpoints';
import type { PaginatedResponse } from '@/api/types';

// ─── Types ───────────────────────────────────────────────────────────────────

export interface StockItem {
  id: number;
  product_name: string;
  available_stock: number;
  reserved_stock: number;
  shipped_stock: number;
  unit: string;
  updated_at: string;
}

export interface CreateStockItemPayload {
  product_name: string;
  available_stock: number;
  reserved_stock?: number;
  shipped_stock?: number;
  unit?: string;
}

export interface UpdateStockItemPayload {
  product_name?: string;
  available_stock?: number;
  reserved_stock?: number;
  shipped_stock?: number;
  unit?: string;
}

// ─── Query Keys ──────────────────────────────────────────────────────────────

export const stockItemKeys = {
  all: ['stock-items'] as const,
  lists: () => [...stockItemKeys.all, 'list'] as const,
  list: (params: Record<string, unknown>) => [...stockItemKeys.lists(), params] as const,
  detail: (id: number) => [...stockItemKeys.all, 'detail', id] as const,
};

// ─── Hooks ───────────────────────────────────────────────────────────────────

interface UseStockListParams {
  page?: number;
  pageSize?: number;
}

/**
 * Fetches paginated list of stock items.
 */
export function useStockList(params: UseStockListParams = {}) {
  const { page = 1, pageSize = 25 } = params;

  return useQuery<PaginatedResponse<StockItem>>({
    queryKey: stockItemKeys.list({ page, pageSize }),
    queryFn: async () => {
      const queryParams: Record<string, string | number> = {
        page,
        page_size: pageSize,
      };
      const response = await apiClient.get(ENDPOINTS.STOCK_ITEMS, {
        params: queryParams,
      });
      return response.data;
    },
  });
}

/**
 * Fetches a single stock item by ID.
 */
export function useStockItem(id: number | null) {
  return useQuery<StockItem>({
    queryKey: stockItemKeys.detail(id!),
    queryFn: async () => {
      const response = await apiClient.get(ENDPOINTS.STOCK_ITEM_DETAIL(id!));
      return response.data;
    },
    enabled: id !== null,
  });
}

/**
 * Creates a new stock item.
 */
export function useCreateStockItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CreateStockItemPayload) => {
      const response = await apiClient.post(ENDPOINTS.STOCK_ITEMS, data);
      return response.data as StockItem;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: stockItemKeys.all });
    },
  });
}

/**
 * Updates an existing stock item.
 */
export function useUpdateStockItem(id: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: UpdateStockItemPayload) => {
      const response = await apiClient.patch(ENDPOINTS.STOCK_ITEM_DETAIL(id), data);
      return response.data as StockItem;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: stockItemKeys.all });
    },
  });
}
