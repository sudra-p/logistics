import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/api/client';
import { ENDPOINTS } from '@/api/endpoints';
import type { ContainerFormValues } from './schema';
import type { ValidationErrorResponse } from '@/api/types';
import type { AxiosError } from 'axios';

/** Container record as returned from the API. */
export interface Container {
  id: number;
  container_type: number;
  container_size: '20FT' | '40FT' | '40FT_HC' | '45FT';
  container_count: number;
  container_no: string;
  seal_no: string;
}

/** Per-field API validation errors for a container entry. */
export type ContainerFieldErrors = Partial<Record<keyof ContainerFormValues, string>>;

/**
 * Hook for managing container entries within a booking.
 * Provides fetching, creating, and deleting containers via the API.
 */
export function useContainers(bookingId: number | null) {
  const queryClient = useQueryClient();

  const queryKey = ['booking-containers', bookingId];

  // ─── Fetch existing containers ─────────────────────────────────────────────
  const containersQuery = useQuery<Container[]>({
    queryKey,
    queryFn: async () => {
      const response = await apiClient.get(
        ENDPOINTS.BOOKING_CONTAINERS(bookingId!),
      );
      const data = response.data;
      // Handle both paginated and flat array responses
      return Array.isArray(data) ? data : data.results ?? [];
    },
    enabled: bookingId !== null,
  });

  // ─── Create container(s) ───────────────────────────────────────────────────
  const createMutation = useMutation<
    Container | Container[],
    AxiosError<ValidationErrorResponse>,
    ContainerFormValues | ContainerFormValues[]
  >({
    mutationFn: async (data) => {
      const response = await apiClient.post(
        ENDPOINTS.BOOKING_CONTAINERS(bookingId!),
        data,
      );
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey });
    },
  });

  // ─── Delete a container ────────────────────────────────────────────────────
  const deleteMutation = useMutation<void, AxiosError, number>({
    mutationFn: async (containerId) => {
      await apiClient.delete(
        ENDPOINTS.BOOKING_CONTAINER_DETAIL(bookingId!, containerId),
      );
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey });
    },
  });

  /**
   * Extracts field-level validation errors from an API 400 response.
   */
  function extractFieldErrors(
    error: AxiosError<ValidationErrorResponse>,
  ): ContainerFieldErrors {
    const fieldErrors: ContainerFieldErrors = {};
    if (error.response?.status === 400 && error.response.data) {
      const data = error.response.data;
      for (const [field, messages] of Object.entries(data)) {
        if (Array.isArray(messages) && messages.length > 0) {
          fieldErrors[field as keyof ContainerFormValues] = messages[0];
        }
      }
    }
    return fieldErrors;
  }

  return {
    containers: containersQuery.data ?? [],
    isLoading: containersQuery.isLoading,
    isError: containersQuery.isError,
    createMutation,
    deleteMutation,
    extractFieldErrors,
  };
}
