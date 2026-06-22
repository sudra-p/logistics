import { useQuery, keepPreviousData } from '@tanstack/react-query';
import apiClient from '@/api/client';
import { ENDPOINTS } from '@/api/endpoints';
import type { PaginatedResponse } from '@/api/types';

export interface BookingSearchResult {
  id: number;
  job_number: string;
  client: string;
  shipping_line: string;
  pol: string;
  pod: string;
  status: string;
  booking_date: string;
}

export interface SearchFilters {
  q: string;
  status: string[];
  shipping_line: string;
  date_from: string;
  date_to: string;
  page: number;
  page_size: number;
}

const DEFAULT_PAGE_SIZE = 25;
const MAX_PAGE_SIZE = 100;
const MIN_QUERY_LENGTH = 1;
const MAX_QUERY_LENGTH = 100;

/**
 * Determines whether the search query is valid for firing an API request.
 * Query must be between 1 and 100 characters (inclusive).
 */
export function isValidSearchQuery(q: string): boolean {
  return q.length >= MIN_QUERY_LENGTH && q.length <= MAX_QUERY_LENGTH;
}

async function fetchBookingSearch(
  filters: SearchFilters,
): Promise<PaginatedResponse<BookingSearchResult>> {
  const params = new URLSearchParams();

  if (filters.q) {
    params.set('q', filters.q);
  }

  if (filters.status.length > 0) {
    params.set('status', filters.status.join(','));
  }

  if (filters.shipping_line) {
    params.set('shipping_line', filters.shipping_line);
  }

  if (filters.date_from) {
    params.set('booking_date_from', filters.date_from);
  }

  if (filters.date_to) {
    params.set('booking_date_to', filters.date_to);
  }

  params.set('page', String(filters.page));
  params.set('page_size', String(Math.min(filters.page_size, MAX_PAGE_SIZE)));
  params.set('ordering', '-booking_date');

  const { data } = await apiClient.get<PaginatedResponse<BookingSearchResult>>(
    `${ENDPOINTS.BOOKING_SEARCH}?${params.toString()}`,
  );
  return data;
}

export function useBookingSearch(filters: SearchFilters) {
  const enabled = isValidSearchQuery(filters.q);

  return useQuery({
    queryKey: ['bookingSearch', filters],
    queryFn: () => fetchBookingSearch(filters),
    enabled,
    placeholderData: keepPreviousData,
    retry: 1,
  });
}

export { DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE };
