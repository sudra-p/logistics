import { Link } from 'react-router-dom';
import { useAuth } from '@/auth/useAuth';
import { useDashboardData } from './useDashboardData';

function MetricCard({
  title,
  value,
  icon,
  trend,
  color,
}: {
  title: string;
  value: number;
  icon: string;
  trend?: string;
  color: 'blue' | 'amber' | 'emerald' | 'purple';
}) {
  const colorMap = {
    blue: {
      bg: 'bg-primary-container/40',
      icon: 'text-primary',
      badge: 'bg-primary/10 text-primary',
    },
    amber: {
      bg: 'bg-amber-50',
      icon: 'text-amber-600',
      badge: 'bg-amber-100 text-amber-700',
    },
    emerald: {
      bg: 'bg-tertiary-container/40',
      icon: 'text-tertiary',
      badge: 'bg-tertiary/10 text-tertiary',
    },
    purple: {
      bg: 'bg-purple-50',
      icon: 'text-purple-600',
      badge: 'bg-purple-100 text-purple-700',
    },
  };

  const colors = colorMap[color];

  return (
    <div className="bg-surface rounded-2xl border border-outline-variant p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className={`w-10 h-10 rounded-xl ${colors.bg} flex items-center justify-center`}>
          <span className={`material-symbols-outlined text-[22px] ${colors.icon}`}>
            {icon}
          </span>
        </div>
        {trend && (
          <span className={`text-body-sm px-2 py-0.5 rounded-full ${colors.badge}`}>
            {trend}
          </span>
        )}
      </div>
      <div>
        <p className="text-headline-md text-on-surface font-semibold">{value}</p>
        <p className="text-body-md text-on-surface-variant mt-0.5">{title}</p>
      </div>
    </div>
  );
}

function AlertItem({
  title,
  description,
  severity,
  time,
}: {
  title: string;
  description: string;
  severity: 'error' | 'warning' | 'info';
  time: string;
}) {
  const severityStyles = {
    error: 'border-l-error bg-error-container/30',
    warning: 'border-l-amber-500 bg-amber-50/50',
    info: 'border-l-primary bg-primary-container/30',
  };

  return (
    <div className={`border-l-[3px] ${severityStyles[severity]} rounded-r-lg p-3`}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-body-md text-on-surface font-medium truncate">{title}</p>
          <p className="text-body-sm text-on-surface-variant mt-0.5">{description}</p>
        </div>
        <span className="text-body-sm text-on-surface-variant whitespace-nowrap">{time}</span>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { user, role } = useAuth();
  const marketingPersonId = user?.marketing_person_id ?? null;
  const { data, isLoading, isError, error, refetch } = useDashboardData(role, marketingPersonId);

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-3 border-primary/30 border-t-primary rounded-full animate-spin" />
          <p className="text-body-md text-on-surface-variant">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div>
        <h1 className="text-headline-lg text-on-surface font-semibold">
          Operations Dashboard
        </h1>
        <div className="mt-4 bg-error-container/40 border border-error/20 rounded-xl p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-error">error</span>
            <p className="text-body-md text-on-error-container">
              {error?.message || 'Dashboard counts could not be loaded. Please try again.'}
            </p>
          </div>
          <button
            onClick={() => { void refetch(); }}
            className="px-4 py-2 text-body-md font-medium text-error hover:bg-error-container rounded-lg transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-headline-lg text-on-surface font-semibold">
            Operations Dashboard
          </h1>
          <p className="text-body-md text-on-surface-variant mt-1">{today}</p>
        </div>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-2 px-4 py-2 border border-outline-variant rounded-xl text-body-md text-on-surface-variant hover:bg-surface-variant transition-colors">
            <span className="material-symbols-outlined text-[18px]">filter_list</span>
            Filter Views
          </button>
          <button className="flex items-center gap-2 px-4 py-2 border border-outline-variant rounded-xl text-body-md text-on-surface-variant hover:bg-surface-variant transition-colors">
            <span className="material-symbols-outlined text-[18px]">download</span>
            Export Data
          </button>
        </div>
      </div>

      {/* Sales role info */}
      {role === 'Sales' && !marketingPersonId && (
        <div className="bg-primary-container/40 border border-primary/20 rounded-xl p-4 flex items-center gap-3">
          <span className="material-symbols-outlined text-primary">info</span>
          <p className="text-body-md text-on-primary-container">
            No marketing person profile is linked to your account. Booking counts cannot be displayed.
          </p>
        </div>
      )}

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Active"
          value={data?.pendingCount ?? 0}
          icon="inventory_2"
          color="blue"
          trend="Pending"
        />
        <MetricCard
          title="En Route"
          value={data?.doBookingEditCount ?? 0}
          icon="local_shipping"
          color="emerald"
          trend="DO/Edit"
        />
        <MetricCard
          title="Upcoming ETD"
          value={data?.upcomingEtdCount ?? 0}
          icon="schedule"
          color="amber"
          trend="7 days"
        />
        <MetricCard
          title="Recent Exports"
          value={data?.recentExportsCount ?? 0}
          icon="task_alt"
          color="purple"
          trend="7 days"
        />
      </div>

      {/* Bento Grid */}
      <div className="grid grid-cols-12 gap-4">
        {/* Map placeholder */}
        <div className="col-span-12 lg:col-span-8 relative h-64 bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <span className="material-symbols-outlined text-white/40 text-5xl">
                public
              </span>
              <p className="text-body-md text-white/60 mt-2">Live Tracking Map</p>
            </div>
          </div>
          <div className="absolute top-4 left-4">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-white/10 backdrop-blur-sm rounded-full text-body-sm text-white/90">
              <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
              Live Global Feed
            </span>
          </div>
        </div>

        {/* Urgent Alerts */}
        <div className="col-span-12 lg:col-span-4 bg-surface rounded-2xl border border-outline-variant p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-title-md text-on-surface font-semibold">Urgent Alerts</h3>
            <span className="inline-flex items-center justify-center w-6 h-6 bg-error-container text-error text-label-sm font-semibold rounded-full">
              3
            </span>
          </div>
          <div className="space-y-3">
            <AlertItem
              title="Vessel Delay — MSC Aurelia"
              description="ETA revised +48h at Jebel Ali"
              severity="error"
              time="2h ago"
            />
            <AlertItem
              title="Documentation pending"
              description="BL draft awaiting approval for JOB-2024-0847"
              severity="warning"
              time="5h ago"
            />
            <AlertItem
              title="Container released"
              description="MSKU-4281739 cleared at JNPT"
              severity="info"
              time="8h ago"
            />
          </div>
        </div>

        {/* Shipment Volume Trends */}
        <div className="col-span-12 bg-surface rounded-2xl border border-outline-variant p-5">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h3 className="text-title-md text-on-surface font-semibold">
                Shipment Volume Trends
              </h3>
              <p className="text-body-sm text-on-surface-variant mt-0.5">
                Weekly throughput — last 8 weeks
              </p>
            </div>
            <div className="flex items-center gap-4 text-body-sm text-on-surface-variant">
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded bg-primary" />
                Exports
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded bg-tertiary" />
                Imports
              </span>
            </div>
          </div>
          <div className="flex items-end justify-between gap-2 h-36">
            {[65, 45, 80, 55, 70, 90, 75, 85].map((height, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <div className="w-full flex gap-0.5">
                  <div
                    className="flex-1 bg-primary/80 rounded-t"
                    style={{ height: `${height}%` }}
                  />
                  <div
                    className="flex-1 bg-tertiary/60 rounded-t"
                    style={{ height: `${Math.max(20, height - 20)}%` }}
                  />
                </div>
                <span className="text-label-sm text-on-surface-variant">
                  W{i + 1}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Admin: Master Data link */}
      {role === 'Admin' && (
        <div className="flex">
          <Link
            to="/master-data"
            className="flex items-center gap-2 px-4 py-2.5 border border-outline-variant rounded-xl text-body-md text-on-surface-variant hover:bg-surface-variant transition-colors"
          >
            <span className="material-symbols-outlined text-[18px]">database</span>
            Manage Master Data
          </Link>
        </div>
      )}
    </div>
  );
}
