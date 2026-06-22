import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Box, Tabs, Tab } from '@mui/material';
import { useAuth } from '@/auth/useAuth';
import { useDashboardKPIs } from './dashboardHooks';
import KPICard from './components/KPICard';
import ProformaStatusSection from './components/ProformaStatusSection';
import ReadyForBookingSection from './components/ReadyForBookingSection';
import CurrentShipmentsSection from './components/CurrentShipmentsSection';
import DocumentStatusSection from './components/DocumentStatusSection';
import AlertsSection from './components/AlertsSection';

export default function DashboardPage() {
  const { role } = useAuth();
  const { data: kpis, isLoading, isError, refetch } = useDashboardKPIs();
  const [activeTab, setActiveTab] = useState(0);

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
              Dashboard could not be loaded. Please try again.
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

      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <KPICard
          title="Total PIs"
          value={kpis?.total_pis ?? 0}
          icon="receipt_long"
          color="primary"
        />
        <KPICard
          title="Pending Payments"
          value={kpis?.pending_payments ?? 0}
          icon="payments"
          color="warning"
        />
        <KPICard
          title="Active Shipments"
          value={kpis?.active_shipments ?? 0}
          icon="local_shipping"
          color="info"
        />
        <KPICard
          title="Containers in Transit"
          value={kpis?.containers_in_transit ?? 0}
          icon="inventory_2"
          color="success"
        />
        <KPICard
          title="Stock Available"
          value={kpis?.stock_available ?? 0}
          icon="warehouse"
          color="info"
        />
      </div>

      {/* Tabbed Workflow Sections */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs
          value={activeTab}
          onChange={(_, newValue) => setActiveTab(newValue)}
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab label="Proforma Status" />
          <Tab label="Ready for Booking" />
          <Tab label="Current Shipments" />
          <Tab label="Documents" />
          <Tab label="Alerts" />
        </Tabs>
      </Box>

      <Box sx={{ pt: 1 }}>
        {activeTab === 0 && <ProformaStatusSection />}
        {activeTab === 1 && <ReadyForBookingSection />}
        {activeTab === 2 && <CurrentShipmentsSection />}
        {activeTab === 3 && <DocumentStatusSection />}
        {activeTab === 4 && <AlertsSection />}
      </Box>

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
