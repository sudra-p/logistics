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
  { path: '/search', allowedRoles: ['Admin', 'Operations', 'Accounts', 'Sales'] },
  { path: '/reports', allowedRoles: ['Admin', 'Operations', 'Accounts'] },
  { path: '/master-data', allowedRoles: ['Admin'] },
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
