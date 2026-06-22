import { useQuery } from '@tanstack/react-query';
import { useState, useMemo } from 'react';
import apiClient from '@/api/client';
import { ENDPOINTS } from '@/api/endpoints';
import type { PaginatedResponse } from '@/api/types';

/** Report row shape (generic — columns vary by report type). */
export interface ReportRow {
  [key: string]: unknown;
}

export type ReportType = 'pending-do' | 'master';
export type ExportFormat = 'csv' | 'excel';

export interface ReportFilters {
  client: string;
  vessel_voyage: string;
  date_from: string;
  date_to: string;
  shipping_line: string;
  status: string;
}

const PAGE_SIZE = 50;

function getDefaultDateFrom(reportType: ReportType): string {
  const now = new Date();
  const days = reportType === 'pending-do' ? 30 : 90;
  const past = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
  return past.toISOString().split('T')[0]!;
}

function getDefaultDateTo(): string {
  return new Date().toISOString().split('T')[0]!;
}

function buildQueryParams(
  reportType: ReportType,
  filters: ReportFilters,
  page: number,
): Record<string, string> {
  const params: Record<string, string> = {
    page: String(page + 1), // API uses 1-based pages
    page_size: String(PAGE_SIZE),
  };

  if (filters.client) params.client = filters.client;
  if (filters.vessel_voyage) params.vessel_voyage = filters.vessel_voyage;
  if (filters.shipping_line) params.shipping_line = filters.shipping_line;

  // Date range params differ by report type
  if (reportType === 'pending-do') {
    params.booking_date_from = filters.date_from || getDefaultDateFrom('pending-do');
    params.booking_date_to = filters.date_to || getDefaultDateTo();
  } else {
    params.created_date_from = filters.date_from || getDefaultDateFrom('master');
    params.created_date_to = filters.date_to || getDefaultDateTo();
    if (filters.status) params.status = filters.status;
  }

  return params;
}

async function fetchReport(
  reportType: ReportType,
  filters: ReportFilters,
  page: number,
): Promise<PaginatedResponse<ReportRow>> {
  const endpoint =
    reportType === 'pending-do' ? ENDPOINTS.REPORT_PENDING_DO : ENDPOINTS.REPORT_MASTER;
  const params = buildQueryParams(reportType, filters, page);
  const { data } = await apiClient.get<PaginatedResponse<ReportRow>>(endpoint, { params });
  return data;
}

export function useReports(reportType: ReportType) {
  const [page, setPage] = useState(0);
  const [filters, setFilters] = useState<ReportFilters>({
    client: '',
    vessel_voyage: '',
    date_from: '',
    date_to: '',
    shipping_line: '',
    status: '',
  });

  const queryKey = useMemo(
    () => ['reports', reportType, filters, page] as const,
    [reportType, filters, page],
  );

  const query = useQuery({
    queryKey,
    queryFn: () => fetchReport(reportType, filters, page),
  });

  const resetPage = () => setPage(0);

  const updateFilters = (newFilters: Partial<ReportFilters>) => {
    setFilters((prev) => ({ ...prev, ...newFilters }));
    resetPage();
  };

  const resetFilters = () => {
    setFilters({
      client: '',
      vessel_voyage: '',
      date_from: '',
      date_to: '',
      shipping_line: '',
      status: '',
    });
    resetPage();
  };

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    page,
    setPage,
    filters,
    updateFilters,
    resetFilters,
    refetch: query.refetch,
  };
}

/**
 * Triggers a file download for report export.
 * Uses axios to fetch the blob with auth headers, then creates a temporary anchor.
 */
export async function exportReport(
  reportType: ReportType,
  format: ExportFormat,
  filters: ReportFilters,
): Promise<void> {
  const endpoint = ENDPOINTS.REPORT_EXPORT(reportType);
  const params: Record<string, string> = { format };

  if (filters.client) params.client = filters.client;
  if (filters.vessel_voyage) params.vessel_voyage = filters.vessel_voyage;
  if (filters.shipping_line) params.shipping_line = filters.shipping_line;

  if (reportType === 'pending-do') {
    if (filters.date_from) params.booking_date_from = filters.date_from;
    if (filters.date_to) params.booking_date_to = filters.date_to;
  } else {
    if (filters.date_from) params.created_date_from = filters.date_from;
    if (filters.date_to) params.created_date_to = filters.date_to;
    if (filters.status) params.status = filters.status;
  }

  const response = await apiClient.get(endpoint, {
    params,
    responseType: 'blob',
  });

  const blob = new Blob([response.data as BlobPart]);
  const extension = format === 'csv' ? 'csv' : 'xlsx';
  const filename = `${reportType}-report.${extension}`;

  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}
