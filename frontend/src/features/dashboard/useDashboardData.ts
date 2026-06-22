import { useQuery } from '@tanstack/react-query';
import apiClient from '@/api/client';
import { ENDPOINTS } from '@/api/endpoints';
import type { PaginatedResponse } from '@/api/types';
import type { Role } from '@/auth/types';

export interface DashboardCounts {
  pendingCount: number;
  doBookingEditCount: number;
  upcomingEtdCount: number;
  recentExportsCount: number;
}

interface BookingSummary {
  id: number;
  status: string;
  etd_pol: string | null;
}

function toDateString(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function getNext7DaysISODate(): string {
  const date = new Date();
  date.setDate(date.getDate() + 7);
  return toDateString(date);
}

function getTodayISODate(): string {
  return toDateString(new Date());
}

function getLast7DaysISODate(): string {
  const date = new Date();
  date.setDate(date.getDate() - 7);
  return toDateString(date);
}

async function fetchCount(params: Record<string, string>): Promise<number> {
  const response = await apiClient.get<PaginatedResponse<BookingSummary>>(
    ENDPOINTS.BOOKINGS,
    { params: { ...params, page_size: '1' } },
  );
  return response.data.count;
}

async function fetchRecentExportsCount(): Promise<number> {
  try {
    const response = await apiClient.get<PaginatedResponse<unknown>>(
      ENDPOINTS.REPORT_PENDING_DO,
      { params: { booking_date_from: getLast7DaysISODate(), page_size: '1' } },
    );
    return response.data.count;
  } catch {
    // If the reports endpoint isn't accessible, return 0
    return 0;
  }
}

async function fetchDashboardCounts(
  role: Role,
  marketingPersonId: number | null,
): Promise<DashboardCounts> {
  const counts: DashboardCounts = {
    pendingCount: 0,
    doBookingEditCount: 0,
    upcomingEtdCount: 0,
    recentExportsCount: 0,
  };

  if (role === 'Sales') {
    if (!marketingPersonId) {
      // No marketing person linked — return zeros
      return counts;
    }

    const [pending, doEdit] = await Promise.all([
      fetchCount({ status: 'PENDING', marketing_person: String(marketingPersonId) }),
      fetchCount({ status: 'DO_BOOKING_EDIT', marketing_person: String(marketingPersonId) }),
    ]);

    counts.pendingCount = pending;
    counts.doBookingEditCount = doEdit;
  } else if (role === 'Accounts') {
    const [pending, recentExports] = await Promise.all([
      fetchCount({ status: 'PENDING' }),
      fetchRecentExportsCount(),
    ]);

    counts.pendingCount = pending;
    counts.recentExportsCount = recentExports;
  } else {
    // Operations and Admin
    const today = getTodayISODate();
    const next7Days = getNext7DaysISODate();

    const [pending, doEdit, upcomingEtd] = await Promise.all([
      fetchCount({ status: 'PENDING' }),
      fetchCount({ status: 'DO_BOOKING_EDIT' }),
      fetchCount({ etd_pol_after: today, etd_pol_before: next7Days }),
    ]);

    counts.pendingCount = pending;
    counts.doBookingEditCount = doEdit;
    counts.upcomingEtdCount = upcomingEtd;
  }

  return counts;
}

export function useDashboardData(role: Role | null, marketingPersonId: number | null) {
  return useQuery<DashboardCounts, Error>({
    queryKey: ['dashboard', role, marketingPersonId],
    queryFn: () => fetchDashboardCounts(role!, marketingPersonId),
    enabled: !!role,
    staleTime: 0,
    refetchOnMount: 'always',
  });
}
