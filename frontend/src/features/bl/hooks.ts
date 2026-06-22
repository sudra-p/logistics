import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/api/client';
import { ENDPOINTS } from '@/api/endpoints';

// ─── Types ───────────────────────────────────────────────────────────────────

export type BLStatus = 'DRAFT' | 'SUBMITTED' | 'RELEASED';
export type BLType = 'LINE' | 'DIRECT';

export interface BillOfLading {
  id: number;
  booking: number;
  bl_number: string;
  bl_type: BLType;
  status: BLStatus;
  container_number: string;
  vessel_name: string;
  voyage_number: string;
  shipper: number;
  shipper_name?: string;
  consignee: number;
  consignee_name?: string;
  notify_party: string;
  cargo_description: string;
  created_by?: number;
  created_at?: string;
  updated_at?: string;
}

export interface CreateBLPayload {
  bl_number: string;
  bl_type: BLType;
  container_number: string;
  vessel_name: string;
  voyage_number: string;
  shipper: number;
  consignee: number;
  notify_party?: string;
  cargo_description?: string;
}

export interface UpdateBLPayload {
  bl_number?: string;
  bl_type?: BLType;
  container_number?: string;
  vessel_name?: string;
  voyage_number?: string;
  shipper?: number;
  consignee?: number;
  notify_party?: string;
  cargo_description?: string;
}

export interface ChangeBLStatusPayload {
  status: BLStatus;
}

// ─── Query Keys ──────────────────────────────────────────────────────────────

export const blKeys = {
  all: ['bills-of-lading'] as const,
  forBooking: (bookingId: number) => [...blKeys.all, 'booking', bookingId] as const,
  detail: (id: number) => [...blKeys.all, 'detail', id] as const,
};

// ─── Hooks ───────────────────────────────────────────────────────────────────

/**
 * Fetches the Bill of Lading for a booking.
 */
export function useBLForBooking(bookingId: number | null) {
  return useQuery<BillOfLading | null>({
    queryKey: blKeys.forBooking(bookingId!),
    queryFn: async () => {
      const response = await apiClient.get(ENDPOINTS.BOOKING_BL(bookingId!));
      const data = response.data;
      // The endpoint returns an array — get the latest BL
      if (Array.isArray(data)) {
        return data.length > 0 ? data[0] : null;
      }
      return data || null;
    },
    enabled: bookingId !== null,
    retry: false,
  });
}

/**
 * Creates a new Bill of Lading for a booking.
 */
export function useCreateBL(bookingId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CreateBLPayload) => {
      const response = await apiClient.post(ENDPOINTS.BOOKING_BL(bookingId), data);
      return response.data as BillOfLading;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: blKeys.all });
    },
  });
}

/**
 * Updates a Bill of Lading.
 */
export function useUpdateBL(blId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: UpdateBLPayload) => {
      const response = await apiClient.patch(ENDPOINTS.BL_DETAIL(blId), data);
      return response.data as BillOfLading;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: blKeys.all });
    },
  });
}

/**
 * Changes the status of a Bill of Lading.
 */
export function useChangeBLStatus(blId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: ChangeBLStatusPayload) => {
      const response = await apiClient.patch(ENDPOINTS.BL_STATUS(blId), data);
      return response.data as BillOfLading;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: blKeys.all });
    },
  });
}
