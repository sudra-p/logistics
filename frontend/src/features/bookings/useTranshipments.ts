import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/api/client';
import { ENDPOINTS } from '@/api/endpoints';

/** Shape of a transhipment leg as returned by the API. */
export interface TranshipmentLeg {
  id: number;
  sequence: number;
  port: number;
  eta: string;
  connecting_vessel_voyage: string;
  etd: string;
}

/** Shape of a new transhipment leg to be sent to the API. */
export interface TranshipmentLegPayload {
  port: number;
  eta: string;
  connecting_vessel_voyage: string;
  etd: string;
}

/**
 * Custom hook for managing transhipment legs within a booking.
 * Handles CRUD operations against the transhipments sub-resource.
 */
export function useTranshipments(bookingId: number | null) {
  const queryClient = useQueryClient();
  const queryKey = ['booking-transhipments', bookingId];

  // ─── Fetch existing legs ───────────────────────────────────────────────────
  const legsQuery = useQuery<TranshipmentLeg[]>({
    queryKey,
    queryFn: async () => {
      if (!bookingId) return [];
      const response = await apiClient.get(ENDPOINTS.BOOKING_TRANSHIPMENTS(bookingId));
      const data = response.data;
      const results: TranshipmentLeg[] = Array.isArray(data) ? data : data.results ?? [];
      // Sort by sequence order
      return results.sort((a, b) => a.sequence - b.sequence);
    },
    enabled: bookingId !== null && bookingId > 0,
  });

  // ─── Create legs (POST with legs array) ────────────────────────────────────
  const createMutation = useMutation({
    mutationFn: async (legs: TranshipmentLegPayload[]) => {
      if (!bookingId) throw new Error('Booking ID is required');
      const response = await apiClient.post(
        ENDPOINTS.BOOKING_TRANSHIPMENTS(bookingId),
        { legs },
      );
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey });
    },
  });

  // ─── Update a single leg (PUT) ────────────────────────────────────────────
  const updateMutation = useMutation({
    mutationFn: async ({
      legId,
      data,
    }: {
      legId: number;
      data: TranshipmentLegPayload;
    }) => {
      if (!bookingId) throw new Error('Booking ID is required');
      const response = await apiClient.put(
        ENDPOINTS.BOOKING_TRANSHIPMENT_DETAIL(bookingId, legId),
        data,
      );
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey });
    },
  });

  // ─── Delete a leg (DELETE) ─────────────────────────────────────────────────
  const deleteMutation = useMutation({
    mutationFn: async (legId: number) => {
      if (!bookingId) throw new Error('Booking ID is required');
      await apiClient.delete(
        ENDPOINTS.BOOKING_TRANSHIPMENT_DETAIL(bookingId, legId),
      );
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey });
    },
  });

  return {
    legs: legsQuery.data ?? [],
    isLoading: legsQuery.isLoading,
    isError: legsQuery.isError,
    refetch: legsQuery.refetch,
    createLegs: createMutation,
    updateLeg: updateMutation,
    deleteLeg: deleteMutation,
  };
}
