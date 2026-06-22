import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/auth/useAuth';
import {
  useBookingSearch,
  isValidSearchQuery,
  DEFAULT_PAGE_SIZE,
  MAX_PAGE_SIZE,
} from './useBookingSearch';
import type { SearchFilters } from './useBookingSearch';
import { useDashboardKPIs } from '@/features/dashboard/dashboardHooks';

const STATUS_OPTIONS = [
  { value: 'PENDING', label: 'Pending' },
  { value: 'BOOKED', label: 'Booked' },
  { value: 'STUFFING', label: 'Stuffing' },
  { value: 'SHIPPED', label: 'Shipped' },
  { value: 'COMPLETED', label: 'Completed' },
] as const;

function StatusPill({ status }: { status: string }) {
  const statusStyles: Record<string, string> = {
    PENDING: 'bg-blue-50 text-blue-700 border-blue-200',
    DO_BOOKING_EDIT: 'bg-amber-50 text-amber-700 border-amber-200',
    COMPLETED: 'bg-slate-100 text-slate-600 border-slate-200',
    IN_TRANSIT: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    DELAYED: 'bg-amber-50 text-amber-700 border-amber-200',
  };

  const style = statusStyles[status] ?? 'bg-slate-50 text-slate-600 border-slate-200';

  const label = status.replace(/_/g, ' ');

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-label-sm font-medium border ${style}`}
    >
      {label}
    </span>
  );
}

function StatCard({ label, value, icon }: { label: string; value: number; icon: string }) {
  return (
    <div className="bg-surface rounded-2xl border border-outline-variant p-4 flex items-center gap-4">
      <div className="w-10 h-10 rounded-xl bg-primary-container/40 flex items-center justify-center">
        <span className="material-symbols-outlined text-primary text-[20px]">{icon}</span>
      </div>
      <div>
        <p className="text-headline-sm text-on-surface font-semibold">{value}</p>
        <p className="text-body-sm text-on-surface-variant">{label}</p>
      </div>
    </div>
  );
}

export default function SearchPage() {
  const navigate = useNavigate();
  const { role } = useAuth();
  const isAccountsRole = role === 'Accounts';

  const [searchInput, setSearchInput] = useState('');
  const [filters, setFilters] = useState<SearchFilters>({
    q: '',
    status: [],
    shipping_line: '',
    date_from: '',
    date_to: '',
    page: 1,
    page_size: DEFAULT_PAGE_SIZE,
  });

  const { data, isError, isLoading, refetch } = useBookingSearch(filters);
  const { data: kpis } = useDashboardKPIs();

  const handleSearch = useCallback(() => {
    if (isValidSearchQuery(searchInput)) {
      setFilters((prev) => ({ ...prev, q: searchInput, page: 1 }));
    }
  }, [searchInput]);

  const handleSearchInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchInput(e.target.value);
  };

  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const handleStatusChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    setFilters((prev) => ({ ...prev, status: value ? [value] : [], page: 1 }));
  };

  const handleShippingLineChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFilters((prev) => ({ ...prev, shipping_line: e.target.value, page: 1 }));
  };

  const handleDateFromChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFilters((prev) => ({ ...prev, date_from: e.target.value, page: 1 }));
  };

  const handleDateToChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFilters((prev) => ({ ...prev, date_to: e.target.value, page: 1 }));
  };

  const handlePageChange = (newPage: number) => {
    setFilters((prev) => ({ ...prev, page: newPage }));
  };

  const handleRowsPerPageChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newPageSize = Math.min(parseInt(e.target.value, 10), MAX_PAGE_SIZE);
    setFilters((prev) => ({ ...prev, page_size: newPageSize, page: 1 }));
  };

  const handleRowClick = (bookingId: number) => {
    if (isAccountsRole) {
      navigate(`/bookings/${String(bookingId)}`);
    } else {
      navigate(`/bookings/${String(bookingId)}/edit`);
    }
  };

  const handleExportCsv = () => {
    const params = new URLSearchParams();
    if (filters.q) params.set('q', filters.q);
    if (filters.status.length > 0) params.set('status', filters.status.join(','));
    if (filters.shipping_line) params.set('shipping_line', filters.shipping_line);
    if (filters.date_from) params.set('booking_date_from', filters.date_from);
    if (filters.date_to) params.set('booking_date_to', filters.date_to);
    window.open(`/api/reports/master/export/?${params.toString()}`, '_blank');
  };

  const hasSearched = filters.q.length > 0;
  const hasResults = data && data.results.length > 0;
  const noResults = hasSearched && data && data.results.length === 0;
  const totalPages = data ? Math.ceil(data.count / filters.page_size) : 0;

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-headline-lg text-on-surface font-semibold">
          Shipment Management
        </h1>
        <p className="text-body-md text-on-surface-variant mt-1">
          Search, filter, and manage freight bookings
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          label="Active Shipments"
          value={kpis?.active_shipments ?? 0}
          icon="inventory_2"
        />
        <StatCard
          label="In Transit"
          value={kpis?.containers_in_transit ?? 0}
          icon="local_shipping"
        />
        <StatCard
          label="Pending"
          value={kpis?.pending_payments ?? 0}
          icon="pending_actions"
        />
      </div>

      {/* Filters bar */}
      <div className="bg-surface rounded-2xl border border-outline-variant p-4">
        <div className="flex flex-wrap items-end gap-3">
          {/* Search */}
          <div className="flex-1 min-w-[200px]">
            <label className="block text-label-md text-on-surface-variant mb-1">
              Search
            </label>
            <div className="relative">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[18px]">
                search
              </span>
              <input
                type="text"
                placeholder="Job number, booking no, client, HBL, MBL..."
                value={searchInput}
                onChange={handleSearchInputChange}
                onKeyDown={handleSearchKeyDown}
                maxLength={100}
                className="w-full pl-9 pr-3 py-2 rounded-xl border border-outline-variant bg-surface-variant/50 text-body-md text-on-surface placeholder:text-on-surface-variant/60 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-colors"
              />
            </div>
          </div>

          {/* Status filter */}
          <div className="min-w-[160px]">
            <label className="block text-label-md text-on-surface-variant mb-1">
              Status
            </label>
            <select
              value={filters.status[0] ?? ''}
              onChange={handleStatusChange}
              className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-variant/50 text-body-md text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
            >
              <option value="">All Statuses</option>
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Date from */}
          <div className="min-w-[150px]">
            <label className="block text-label-md text-on-surface-variant mb-1">
              Date From
            </label>
            <input
              type="date"
              value={filters.date_from}
              onChange={handleDateFromChange}
              className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-variant/50 text-body-md text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
            />
          </div>

          {/* Date to */}
          <div className="min-w-[150px]">
            <label className="block text-label-md text-on-surface-variant mb-1">
              Date To
            </label>
            <input
              type="date"
              value={filters.date_to}
              onChange={handleDateToChange}
              className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-variant/50 text-body-md text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
            />
          </div>

          {/* Shipping line */}
          <div className="min-w-[140px]">
            <label className="block text-label-md text-on-surface-variant mb-1">
              Shipping Line
            </label>
            <input
              type="text"
              placeholder="All lines"
              value={filters.shipping_line}
              onChange={handleShippingLineChange}
              className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-variant/50 text-body-md text-on-surface placeholder:text-on-surface-variant/60 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
            />
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={handleSearch}
              disabled={!isValidSearchQuery(searchInput)}
              className="px-4 py-2 bg-primary text-on-primary rounded-xl text-body-md font-medium hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Search
            </button>
            <button
              onClick={handleExportCsv}
              className="flex items-center gap-1.5 px-4 py-2 border border-outline-variant rounded-xl text-body-md text-on-surface-variant hover:bg-surface-variant transition-colors"
            >
              <span className="material-symbols-outlined text-[16px]">download</span>
              CSV
            </button>
          </div>
        </div>
      </div>

      {/* Error State */}
      {isError && (
        <div className="bg-error-container/40 border border-error/20 rounded-xl p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-error">error</span>
            <p className="text-body-md text-on-error-container">
              Results could not be loaded. Please try again.
            </p>
          </div>
          <button
            onClick={() => { void refetch(); }}
            className="px-4 py-2 text-body-md font-medium text-error hover:bg-error-container rounded-lg transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* No Results */}
      {noResults && (
        <div className="bg-primary-container/30 border border-primary/10 rounded-xl p-4 flex items-center gap-3">
          <span className="material-symbols-outlined text-primary">info</span>
          <p className="text-body-md text-on-primary-container">
            No bookings match the search criteria.
          </p>
        </div>
      )}

      {/* Loading */}
      {isLoading && hasSearched && (
        <div className="flex items-center gap-3 py-4">
          <div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
          <p className="text-body-md text-on-surface-variant">Loading results...</p>
        </div>
      )}

      {/* Results Table */}
      {hasResults && (
        <div className="bg-surface rounded-2xl border border-outline-variant overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-outline-variant bg-surface-variant/50">
                  <th className="px-4 py-3 text-label-lg text-on-surface-variant font-medium">
                    Job Number
                  </th>
                  <th className="px-4 py-3 text-label-lg text-on-surface-variant font-medium">
                    Status
                  </th>
                  <th className="px-4 py-3 text-label-lg text-on-surface-variant font-medium">
                    Origin (POL)
                  </th>
                  <th className="px-4 py-3 text-label-lg text-on-surface-variant font-medium">
                    Destination (POD)
                  </th>
                  <th className="px-4 py-3 text-label-lg text-on-surface-variant font-medium">
                    Client
                  </th>
                  <th className="px-4 py-3 text-label-lg text-on-surface-variant font-medium">
                    Shipping Line
                  </th>
                  <th className="px-4 py-3 text-label-lg text-on-surface-variant font-medium">
                    Booking Date
                  </th>
                  <th className="px-4 py-3 text-label-lg text-on-surface-variant font-medium">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant">
                {data.results.map((row) => (
                  <tr
                    key={row.id}
                    onClick={() => { handleRowClick(row.id); }}
                    className="hover:bg-surface-variant/50 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3 text-body-md text-on-surface font-medium font-mono">
                      {row.job_number}
                    </td>
                    <td className="px-4 py-3">
                      <StatusPill status={row.status} />
                    </td>
                    <td className="px-4 py-3 text-body-md text-on-surface">
                      {row.pol}
                    </td>
                    <td className="px-4 py-3 text-body-md text-on-surface">
                      {row.pod}
                    </td>
                    <td className="px-4 py-3 text-body-md text-on-surface">
                      {row.client}
                    </td>
                    <td className="px-4 py-3 text-body-md text-on-surface-variant">
                      {row.shipping_line}
                    </td>
                    <td className="px-4 py-3 text-body-md text-on-surface-variant">
                      {row.booking_date}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRowClick(row.id);
                        }}
                        className="p-1.5 rounded-lg hover:bg-surface-variant text-on-surface-variant"
                        aria-label="View booking"
                      >
                        <span className="material-symbols-outlined text-[18px]">
                          open_in_new
                        </span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-4 py-3 border-t border-outline-variant bg-surface-variant/30">
            <div className="flex items-center gap-2 text-body-sm text-on-surface-variant">
              <span>
                Showing {(filters.page - 1) * filters.page_size + 1}–
                {Math.min(filters.page * filters.page_size, data.count)} of{' '}
                {data.count}
              </span>
              <span className="text-outline">|</span>
              <label className="flex items-center gap-1.5">
                Rows:
                <select
                  value={filters.page_size}
                  onChange={handleRowsPerPageChange}
                  className="px-2 py-1 rounded-lg border border-outline-variant bg-surface text-body-sm focus:outline-none focus:ring-1 focus:ring-primary/30"
                >
                  {[10, 25, 50, 100].map((size) => (
                    <option key={size} value={size}>
                      {size}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => { handlePageChange(filters.page - 1); }}
                disabled={filters.page <= 1}
                className="p-2 rounded-lg hover:bg-surface-variant text-on-surface-variant disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                aria-label="Previous page"
              >
                <span className="material-symbols-outlined text-[20px]">
                  chevron_left
                </span>
              </button>
              <span className="text-body-sm text-on-surface px-2">
                Page {filters.page} of {totalPages}
              </span>
              <button
                onClick={() => { handlePageChange(filters.page + 1); }}
                disabled={filters.page >= totalPages}
                className="p-2 rounded-lg hover:bg-surface-variant text-on-surface-variant disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                aria-label="Next page"
              >
                <span className="material-symbols-outlined text-[20px]">
                  chevron_right
                </span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Bottom section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Map placeholder */}
        <div className="relative h-48 bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl overflow-hidden">
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <span className="material-symbols-outlined text-white/40 text-4xl">
                map
              </span>
              <p className="text-body-sm text-white/60 mt-1">Route Visualization</p>
            </div>
          </div>
        </div>

        {/* Carrier performance */}
        <div className="bg-surface rounded-2xl border border-outline-variant p-5">
          <h3 className="text-title-md text-on-surface font-semibold mb-3">
            Carrier Performance
          </h3>
          <div className="space-y-3">
            {[
              { name: 'MSC', onTime: 94 },
              { name: 'Maersk', onTime: 91 },
              { name: 'CMA CGM', onTime: 88 },
            ].map((carrier) => (
              <div key={carrier.name} className="flex items-center gap-3">
                <span className="text-body-md text-on-surface w-20">{carrier.name}</span>
                <div className="flex-1 h-2 bg-surface-variant rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary rounded-full"
                    style={{ width: `${String(carrier.onTime)}%` }}
                  />
                </div>
                <span className="text-body-sm text-on-surface-variant w-10 text-right">
                  {carrier.onTime}%
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Create Booking button (for non-Accounts roles) */}
      {!isAccountsRole && (
        <div className="flex">
          <button
            onClick={() => { navigate('/bookings/new'); }}
            className="flex items-center gap-2 px-5 py-2.5 bg-primary text-on-primary rounded-xl font-medium text-body-md hover:bg-primary/90 transition-colors"
          >
            <span className="material-symbols-outlined text-[18px]">add</span>
            Create Booking
          </button>
        </div>
      )}
    </div>
  );
}
