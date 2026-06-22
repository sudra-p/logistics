import type { Role } from '@/auth/types';

export interface RoutePermission {
  path: string;
  allowedRoles: Role[];
  restrictions?: Partial<Record<Role, string[]>>;
}

export const routePermissions: RoutePermission[] = [
  { path: '/dashboard', allowedRoles: ['Admin', 'Operations', 'Accounts', 'Sales'] },
  { path: '/bookings/new', allowedRoles: ['Admin', 'Operations'] },
  { path: '/bookings/:id/edit', allowedRoles: ['Admin', 'Operations'] },
  { path: '/bookings/:id', allowedRoles: ['Admin', 'Operations', 'Accounts', 'Sales'] },
  { path: '/bookings/:id/bl', allowedRoles: ['Admin', 'Operations'] },
  { path: '/bookings/:id/bl/new', allowedRoles: ['Admin', 'Operations'] },
  { path: '/bookings/:id/bl/edit', allowedRoles: ['Admin', 'Operations'] },
  { path: '/bookings/:id/commercial-invoice', allowedRoles: ['Admin', 'Accounts', 'Operations'] },
  { path: '/bookings/:id/packing-list', allowedRoles: ['Admin', 'Accounts', 'Operations'] },
  { path: '/search', allowedRoles: ['Admin', 'Operations', 'Accounts', 'Sales'] },
  { path: '/reports', allowedRoles: ['Admin', 'Operations', 'Accounts'] },
  { path: '/master-data', allowedRoles: ['Admin'] },
  { path: '/proforma', allowedRoles: ['Admin', 'Accounts', 'Sales'] },
  { path: '/proforma/new', allowedRoles: ['Admin', 'Accounts'] },
  { path: '/proforma/:id/edit', allowedRoles: ['Admin', 'Accounts'] },
  { path: '/proforma/:id', allowedRoles: ['Admin', 'Accounts', 'Sales'] },
  { path: '/payments', allowedRoles: ['Admin', 'Accounts'] },
  { path: '/payments/new', allowedRoles: ['Admin', 'Accounts'] },
  { path: '/inventory', allowedRoles: ['Admin', 'Operations'] },
  { path: '/inventory/new', allowedRoles: ['Admin', 'Operations'] },
  { path: '/inventory/:id/edit', allowedRoles: ['Admin', 'Operations'] },
  { path: '/operations', allowedRoles: ['Admin', 'Operations'] },
  { path: '/profile', allowedRoles: ['Admin', 'Operations', 'Accounts', 'Sales'] },
  { path: '/access-denied', allowedRoles: ['Admin', 'Operations', 'Accounts', 'Sales'] },
];

/**
 * Checks whether a given role has access to a specific path.
 * Supports parameterized route matching (e.g. /bookings/:id matches /bookings/42).
 */
export function hasRouteAccess(role: Role, pathname: string): boolean {
  return routePermissions.some((perm) => {
    if (perm.path === pathname) {
      return perm.allowedRoles.includes(role);
    }
    // Convert route pattern to regex for parameterized matching
    const pattern = perm.path.replace(/:[\w]+/g, '[^/]+');
    const regex = new RegExp(`^${pattern}$`);
    if (regex.test(pathname)) {
      return perm.allowedRoles.includes(role);
    }
    return false;
  });
}
