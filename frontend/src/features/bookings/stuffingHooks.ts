import { useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/api/client';
import { ENDPOINTS } from '@/api/endpoints';

// ─── Types ───────────────────────────────────────────────────────────────────

export interface StuffingProduct {
  product_name: string;
  quantity: number;
}

export interface PerformStuffingPayload {
  products: StuffingProduct[];
}

// ─── Hooks ───────────────────────────────────────────────────────────────────

/**
 * Performs the stuffing action on a container.
 * POST /api/bookings/{id}/containers/{cid}/stuff/
 */
export function usePerformStuffing(bookingId: number, containerId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: PerformStuffingPayload) => {
      const response = await apiClient.post(
        ENDPOINTS.CONTAINER_STUFF(bookingId, containerId),
        data
      );
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['bookings'] });
      void queryClient.invalidateQueries({ queryKey: ['stock-items'] });
    },
  });
}
