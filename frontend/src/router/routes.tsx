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

      {/* Default redirect */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />

      {/* Catch-all: redirect to dashboard */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
