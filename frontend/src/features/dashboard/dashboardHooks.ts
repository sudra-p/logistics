import { useQuery } from '@tanstack/react-query';
import apiClient from '@/api/client';
import { ENDPOINTS } from '@/api/endpoints';

// ─── Types ───────────────────────────────────────────────────────────────────

export interface DashboardKPIs {
  total_pis: number;
  pending_payments: number;
  active_shipments: number;
  containers_in_transit: number;
  stock_available: number;
}

export interface ProformaStatusItem {
  id: number;
  pi_number: string;
  customer_name: string;
  total_amount: string;
  status: string;
}

export interface ReadyForBookingItem {
  id: number;
  pi_number: string;
  customer_name: string;
  total_amount: string;
  expected_shipment_date: string;
}

export interface CurrentShipmentItem {
  id: number;
  job_number: string;
  customer_name: string;
  container_number: string;
  status: string;
  etd: string | null;
  eta: string | null;
}

export interface DocumentStatusData {
  pending_commercial_invoices: number;
  pending_packing_lists: number;
  pending_bls: number;
}

export interface AlertItem {
  id: string;
  title: string;
  description: string;
  severity: 'error' | 'warning' | 'info';
  type: string;
}

// ─── Query Keys ──────────────────────────────────────────────────────────────

export const dashboardKeys = {
  kpis: ['dashboard', 'kpis'] as const,
  proformaStatus: ['dashboard', 'proforma-status'] as const,
  readyForBooking: ['dashboard', 'ready-for-booking'] as const,
  currentShipments: ['dashboard', 'current-shipments'] as const,
  documentStatus: ['dashboard', 'document-status'] as const,
  alerts: ['dashboard', 'alerts'] as const,
};

// ─── Hooks ───────────────────────────────────────────────────────────────────

export function useDashboardKPIs() {
  return useQuery<DashboardKPIs>({
    queryKey: dashboardKeys.kpis,
    queryFn: async () => {
      const response = await apiClient.get(ENDPOINTS.DASHBOARD_KPIS);
      return response.data;
    },
    staleTime: 30_000,
    refetchOnMount: 'always',
  });
}

export function useProformaStatus() {
  return useQuery<ProformaStatusItem[]>({
    queryKey: dashboardKeys.proformaStatus,
    queryFn: async () => {
      const response = await apiClient.get(ENDPOINTS.DASHBOARD_PROFORMA_STATUS);
      return response.data?.results ?? response.data ?? [];
    },
    staleTime: 30_000,
  });
}

export function useReadyForBooking() {
  return useQuery<ReadyForBookingItem[]>({
    queryKey: dashboardKeys.readyForBooking,
    queryFn: async () => {
      const response = await apiClient.get(ENDPOINTS.DASHBOARD_READY_FOR_BOOKING);
      return response.data?.results ?? response.data ?? [];
    },
    staleTime: 30_000,
  });
}

export function useCurrentShipments() {
  return useQuery<CurrentShipmentItem[]>({
    queryKey: dashboardKeys.currentShipments,
    queryFn: async () => {
      const response = await apiClient.get(ENDPOINTS.DASHBOARD_CURRENT_SHIPMENTS);
      return response.data?.results ?? response.data ?? [];
    },
    staleTime: 30_000,
  });
}

export function useDocumentStatus() {
  return useQuery<DocumentStatusData>({
    queryKey: dashboardKeys.documentStatus,
    queryFn: async () => {
      const response = await apiClient.get(ENDPOINTS.DASHBOARD_DOCUMENT_STATUS);
      return response.data;
    },
    staleTime: 30_000,
  });
}

export function useAlerts() {
  return useQuery<AlertItem[]>({
    queryKey: dashboardKeys.alerts,
    queryFn: async () => {
      const response = await apiClient.get(ENDPOINTS.DASHBOARD_ALERTS);
      return response.data?.results ?? response.data ?? [];
    },
    staleTime: 30_000,
  });
}
