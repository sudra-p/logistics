import { Navigate, useLocation } from 'react-router-dom';
import { Box, Typography, Button } from '@mui/material';
import { useAuth } from '@/auth/useAuth';
import { hasRouteAccess } from './routePermissions';
import type { Role } from '@/auth/types';

interface RoleGuardProps {
  allowedRoles?: Role[];
  children: React.ReactNode;
}

/**
 * RoleGuard protects routes based on authentication and role.
 *
 * Behavior:
 * - Unauthenticated users → redirect to /login with intended path stored in state.from
 * - Authenticated users without route permission → show unauthorized message + Dashboard link
 * - Authenticated users with permission → render children
 */
export function RoleGuard({ allowedRoles, children }: RoleGuardProps) {
  const { isAuthenticated, role } = useAuth();
  const location = useLocation();

  // Unauthenticated → redirect to login, preserve intended path
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  // Check role permission: use explicit allowedRoles prop if provided,
  // otherwise fall back to path-based permission lookup
  const hasAccess = allowedRoles
    ? role !== null && allowedRoles.includes(role)
    : role !== null && hasRouteAccess(role, location.pathname);

  if (!hasAccess) {
    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '60vh',
          gap: 2,
          p: 3,
        }}
      >
        <Typography variant="h5" component="h1">
          Unauthorized Access
        </Typography>
        <Typography variant="body1" color="text.secondary">
          You do not have permission to access this page.
        </Typography>
        <Button variant="contained" href="/dashboard">
          Go to Dashboard
        </Button>
      </Box>
    );
  }

  return <>{children}</>;
}
