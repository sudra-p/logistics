import { useEffect, useMemo } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/api/client';
import { ENDPOINTS } from '@/api/endpoints';
import { bookingSchema } from './schema';
import type { BookingFormValues } from './schema';
import type { ValidationErrorResponse } from '@/api/types';
import type { AxiosError } from 'axios';

/** Master data option used in dropdowns. */
export interface MasterDataOption {
  id: number;
  name: string;
}

/** Dropdown field metadata for loading master data. */
interface DropdownConfig {
  field: keyof BookingFormValues;
  entityType: string;
  label: string;
}

/** All foreign-key dropdown fields that need master data loading. */
export const DROPDOWN_FIELDS: DropdownConfig[] = [
  { field: 'shipping_line', entityType: 'shipping-lines', label: 'Shipping Line' },
  { field: 'pol', entityType: 'ports', label: 'Port of Loading' },
  { field: 'pod', entityType: 'ports', label: 'Port of Discharge' },
  { field: 'client', entityType: 'clients', label: 'Client' },
  { field: 'commodity', entityType: 'commodities', label: 'Commodity' },
];

/** Status of a dropdown's data loading. */
export interface DropdownState {
  options: MasterDataOption[];
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
}

const DEFAULT_VALUES: BookingFormValues = {
  booking_date: '',
  booking_validity_date: '',
  forwarding_window_start: '',
  forwarding_window_end: '',
  shipping_line: 0 as unknown as number,
  pol: 0 as unknown as number,
  pod: 0 as unknown as number,
  client: 0 as unknown as number,
  commodity: 0 as unknown as number,
  cargo_type: 'FCL',
  shipment_type: '',
  stuffing_type: '',
  is_haz: false,
  haz_class: '',
  haz_uin: '',
  haz_group: '',
};

/**
 * Fetches active master data entities for a given entity type.
 */
function useMasterDataOptions(entityType: string) {
  return useQuery<MasterDataOption[]>({
    queryKey: ['master-data', entityType, 'active'],
    queryFn: async () => {
      const response = await apiClient.get(
        ENDPOINTS.MASTER_DATA(entityType),
        { params: { is_active: true, page_size: 1000 } },
      );
      // Handle both paginated and flat array responses
      const data = response.data;
      const results = Array.isArray(data) ? data : data.results ?? [];
      return results.map((item: { id: number; name: string }) => ({
        id: item.id,
        name: item.name,
      }));
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Custom hook encapsulating all booking form logic:
 * - Form state via react-hook-form + zod resolver
 * - Detect create vs edit mode from URL params
 * - Load existing booking data for editing
 * - Load master data for dropdowns
 * - Submit via POST (create) or PATCH (edit)
 * - Map API 400 errors to form fields
 */
export function useBookingForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const isEditMode = !!id;
  const bookingId = id ? Number(id) : null;

  // ─── Form setup ────────────────────────────────────────────────────────────
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const form = useForm<BookingFormValues>({
    resolver: zodResolver(bookingSchema) as any,
    defaultValues: DEFAULT_VALUES,
    mode: 'onBlur',
  });

  // ─── Load existing booking for edit mode ───────────────────────────────────
  const bookingQuery = useQuery({
    queryKey: ['booking', bookingId],
    queryFn: async () => {
      const response = await apiClient.get(ENDPOINTS.BOOKING_DETAIL(bookingId!));
      return response.data;
    },
    enabled: isEditMode && bookingId !== null,
    retry: 1,
  });

  // Pre-populate form when booking data loads
  useEffect(() => {
    if (bookingQuery.data) {
      const booking = bookingQuery.data;
      form.reset({
        booking_date: booking.booking_date ?? '',
        booking_validity_date: booking.booking_validity_date ?? '',
        forwarding_window_start: booking.forwarding_window_start ?? '',
        forwarding_window_end: booking.forwarding_window_end ?? '',
        shipping_line: booking.shipping_line ?? 0,
        pol: booking.pol ?? 0,
        pod: booking.pod ?? 0,
        client: booking.client ?? 0,
        commodity: booking.commodity ?? 0,
        cargo_type: booking.cargo_type ?? 'FCL',
        shipment_type: booking.shipment_type ?? '',
        stuffing_type: booking.stuffing_type ?? '',
        is_haz: booking.is_haz ?? false,
        haz_class: booking.haz_class ?? '',
        haz_uin: booking.haz_uin ?? '',
        haz_group: booking.haz_group ?? '',
      });
    }
  }, [bookingQuery.data, form]);

  // ─── Master data dropdowns ─────────────────────────────────────────────────
  const shippingLineQuery = useMasterDataOptions('shipping-lines');
  const polQuery = useMasterDataOptions('ports');
  const podQuery = useMasterDataOptions('ports');
  const clientQuery = useMasterDataOptions('clients');
  const commodityQuery = useMasterDataOptions('commodities');

  const dropdowns: Record<string, DropdownState> = useMemo(
    () => ({
      shipping_line: {
        options: shippingLineQuery.data ?? [],
        isLoading: shippingLineQuery.isLoading,
        isError: shippingLineQuery.isError,
        errorMessage: shippingLineQuery.isError ? 'Failed to load shipping lines' : null,
      },
      pol: {
        options: polQuery.data ?? [],
        isLoading: polQuery.isLoading,
        isError: polQuery.isError,
        errorMessage: polQuery.isError ? 'Failed to load ports' : null,
      },
      pod: {
        options: podQuery.data ?? [],
        isLoading: podQuery.isLoading,
        isError: podQuery.isError,
        errorMessage: podQuery.isError ? 'Failed to load ports' : null,
      },
      client: {
        options: clientQuery.data ?? [],
        isLoading: clientQuery.isLoading,
        isError: clientQuery.isError,
        errorMessage: clientQuery.isError ? 'Failed to load clients' : null,
      },
      commodity: {
        options: commodityQuery.data ?? [],
        isLoading: commodityQuery.isLoading,
        isError: commodityQuery.isError,
        errorMessage: commodityQuery.isError ? 'Failed to load commodities' : null,
      },
    }),
    [shippingLineQuery, polQuery, podQuery, clientQuery, commodityQuery],
  );

  // ─── Submission ────────────────────────────────────────────────────────────
  const submitMutation = useMutation({
    mutationFn: async (data: BookingFormValues) => {
      if (isEditMode && bookingId) {
        const response = await apiClient.patch(
          ENDPOINTS.BOOKING_DETAIL(bookingId),
          data,
        );
        return response.data;
      }
      const response = await apiClient.post(ENDPOINTS.BOOKINGS, data);
      return response.data;
    },
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ['bookings'] });
      const resultId = data.id as number;
      navigate(`/bookings/${resultId}`);
    },
    onError: (error: AxiosError<ValidationErrorResponse>) => {
      if (error.response?.status === 400 && error.response.data) {
        const fieldErrors = error.response.data;
        for (const [field, messages] of Object.entries(fieldErrors)) {
          if (Array.isArray(messages) && messages.length > 0) {
            form.setError(field as keyof BookingFormValues, {
              type: 'server',
              message: messages[0],
            });
          }
        }
      }
    },
  });

  const onSubmit = form.handleSubmit((data) => {
    submitMutation.mutate(data as BookingFormValues);
  });

  return {
    form,
    isEditMode,
    bookingId,
    bookingQuery,
    dropdowns,
    submitMutation,
    onSubmit,
    DROPDOWN_FIELDS,
  };
}
