import { Routes, Route, Navigate } from 'react-router-dom';
import { RoleGuard } from './RoleGuard';
import { Layout } from '@/components/Layout';
import LoginPage from '@/features/auth/LoginPage';
import DashboardPage from '@/features/dashboard/DashboardPage';
import BookingFormPage from '@/features/bookings/BookingFormPage';
import BookingDetailPage from '@/features/bookings/BookingDetailPage';
import SearchPage from '@/features/search/SearchPage';
import ReportsPage from '@/features/reports/ReportsPage';
import MasterDataPage from '@/features/master-data/MasterDataPage';
import ProfilePage from '@/features/profile/ProfilePage';
import ProformaListPage from '@/features/proforma/ProformaListPage';
import ProformaFormPage from '@/features/proforma/ProformaFormPage';
import ProformaDetailPage from '@/features/proforma/ProformaDetailPage';
import PaymentListPage from '@/features/payments/PaymentListPage';
import PaymentFormPage from '@/features/payments/PaymentFormPage';
import StockListPage from '@/features/inventory/StockListPage';
import StockFormPage from '@/features/inventory/StockFormPage';
import CommercialInvoicePage from '@/features/invoices/CommercialInvoicePage';
import PackingListPage from '@/features/invoices/PackingListPage';
import BLFormPage from '@/features/bl/BLFormPage';
import BLDetailPage from '@/features/bl/BLDetailPage';
import OperationsPage from '@/features/operations/OperationsPage';
import AccessDenied from '@/components/AccessDenied';

function ProtectedLayout({ children }: { children: React.ReactNode }) {
  return (
    <Layout>
      {children}
    </Layout>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      {/* Public route — no layout */}
      <Route path="/login" element={<LoginPage />} />

      {/* Access Denied page */}
      <Route
        path="/access-denied"
        element={
          <ProtectedLayout>
            <AccessDenied />
          </ProtectedLayout>
        }
      />

      {/* Protected routes — wrapped in Layout */}
      <Route
        path="/dashboard"
        element={
          <RoleGuard allowedRoles={['Admin', 'Operations', 'Accounts', 'Sales']}>
            <ProtectedLayout>
              <DashboardPage />
            </ProtectedLayout>
          </RoleGuard>
        }
      />

      <Route
        path="/bookings/new"
        element={
          <RoleGuard allowedRoles={['Admin', 'Operations']}>
            <ProtectedLayout>
              <BookingFormPage />
            </ProtectedLayout>
          </RoleGuard>
        }
      />

      <Route
        path="/bookings/:id/edit"
        element={
          <RoleGuard allowedRoles={['Admin', 'Operations']}>
            <ProtectedLayout>
              <BookingFormPage />
            </ProtectedLayout>
          </RoleGuard>
        }
      />

      <Route
        path="/bookings/:id"
        element={
          <RoleGuard allowedRoles={['Admin', 'Operations', 'Accounts', 'Sales']}>
            <ProtectedLayout>
              <BookingDetailPage />
            </ProtectedLayout>
          </RoleGuard>
        }
      />

      {/* BL routes */}
      <Route
        path="/bookings/:id/bl"
        element={
          <RoleGuard allowedRoles={['Admin', 'Operations']}>
            <ProtectedLayout>
              <BLDetailPage />
            </ProtectedLayout>
          </RoleGuard>
        }
      />

      <Route
        path="/bookings/:id/bl/new"
        element={
          <RoleGuard allowedRoles={['Admin', 'Operations']}>
            <ProtectedLayout>
              <BLFormPage />
            </ProtectedLayout>
          </RoleGuard>
        }
      />

      <Route
        path="/bookings/:id/bl/edit"
        element={
          <RoleGuard allowedRoles={['Admin', 'Operations']}>
            <ProtectedLayout>
              <BLFormPage />
            </ProtectedLayout>
          </RoleGuard>
        }
      />

      <Route
        path="/search"
        element={
          <RoleGuard allowedRoles={['Admin', 'Operations', 'Accounts', 'Sales']}>
            <ProtectedLayout>
              <SearchPage />
            </ProtectedLayout>
          </RoleGuard>
        }
      />

      <Route
        path="/reports"
        element={
          <RoleGuard allowedRoles={['Admin', 'Operations', 'Accounts']}>
            <ProtectedLayout>
              <ReportsPage />
            </ProtectedLayout>
          </RoleGuard>
        }
      />

      <Route
        path="/master-data"
        element={
          <RoleGuard allowedRoles={['Admin']}>
            <ProtectedLayout>
              <MasterDataPage />
            </ProtectedLayout>
          </RoleGuard>
        }
      />

      <Route
        path="/profile"
        element={
          <RoleGuard allowedRoles={['Admin', 'Operations', 'Accounts', 'Sales']}>
            <ProtectedLayout>
              <ProfilePage />
            </ProtectedLayout>
          </RoleGuard>
        }
      />

      {/* Proforma Invoice routes */}
      <Route
        path="/proforma"
        element={
          <RoleGuard allowedRoles={['Admin', 'Accounts', 'Sales']}>
            <ProtectedLayout>
              <ProformaListPage />
            </ProtectedLayout>
          </RoleGuard>
        }
      />

      <Route
        path="/proforma/new"
        element={
          <RoleGuard allowedRoles={['Admin', 'Accounts']}>
            <ProtectedLayout>
              <ProformaFormPage />
            </ProtectedLayout>
          </RoleGuard>
        }
      />

      <Route
        path="/proforma/:id/edit"
        element={
          <RoleGuard allowedRoles={['Admin', 'Accounts']}>
            <ProtectedLayout>
              <ProformaFormPage />
            </ProtectedLayout>
          </RoleGuard>
        }
      />

      <Route
        path="/proforma/:id"
        element={
          <RoleGuard allowedRoles={['Admin', 'Accounts', 'Sales']}>
            <ProtectedLayout>
              <ProformaDetailPage />
            </ProtectedLayout>
          </RoleGuard>
        }
      />

      {/* Payment routes */}
      <Route
        path="/payments"
        element={
          <RoleGuard allowedRoles={['Admin', 'Accounts']}>
            <ProtectedLayout>
              <PaymentListPage />
            </ProtectedLayout>
          </RoleGuard>
        }
      />

      <Route
        path="/payments/new"
        element={
          <RoleGuard allowedRoles={['Admin', 'Accounts']}>
            <ProtectedLayout>
              <PaymentFormPage />
            </ProtectedLayout>
          </RoleGuard>
        }
      />

      {/* Inventory / Stock routes */}
      <Route
        path="/inventory"
        element={
          <RoleGuard allowedRoles={['Admin', 'Operations']}>
            <ProtectedLayout>
              <StockListPage />
            </ProtectedLayout>
          </RoleGuard>
        }
      />

      <Route
        path="/inventory/new"
        element={
          <RoleGuard allowedRoles={['Admin', 'Operations']}>
            <ProtectedLayout>
              <StockFormPage />
            </ProtectedLayout>
          </RoleGuard>
        }
      />

      <Route
        path="/inventory/:id/edit"
        element={
          <RoleGuard allowedRoles={['Admin', 'Operations']}>
            <ProtectedLayout>
              <StockFormPage />
            </ProtectedLayout>
          </RoleGuard>
        }
      />

      {/* Commercial Invoice & Packing List routes (accessed from booking context) */}
      <Route
        path="/bookings/:id/commercial-invoice"
        element={
          <RoleGuard allowedRoles={['Admin', 'Accounts', 'Operations']}>
            <ProtectedLayout>
              <CommercialInvoicePage />
            </ProtectedLayout>
          </RoleGuard>
        }
      />

      <Route
        path="/bookings/:id/packing-list"
        element={
          <RoleGuard allowedRoles={['Admin', 'Accounts', 'Operations']}>
            <ProtectedLayout>
              <PackingListPage />
            </ProtectedLayout>
          </RoleGuard>
        }
      />

      {/* Operations View */}
      <Route
        path="/operations"
        element={
          <RoleGuard allowedRoles={['Admin', 'Operations']}>
            <ProtectedLayout>
              <OperationsPage />
            </ProtectedLayout>
          </RoleGuard>
        }
      />

      {/* Default redirect */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />

      {/* Catch-all: redirect to dashboard */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
