import { useState, useRef, useEffect } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '@/auth/useAuth';
import type { Role } from '@/auth/types';

interface NavItem {
  label: string;
  path: string;
  icon: string;
  allowedRoles: Role[];
}

const navItems: NavItem[] = [
  {
    label: 'Dashboard',
    path: '/dashboard',
    icon: 'dashboard',
    allowedRoles: ['Admin', 'Operations', 'Accounts', 'Sales'],
  },
  {
    label: 'Bookings',
    path: '/search',
    icon: 'local_shipping',
    allowedRoles: ['Admin', 'Operations', 'Accounts', 'Sales'],
  },
  {
    label: 'Operations',
    path: '/operations',
    icon: 'hub',
    allowedRoles: ['Admin', 'Operations'],
  },
  {
    label: 'Proforma Invoices',
    path: '/proforma',
    icon: 'receipt_long',
    allowedRoles: ['Admin', 'Accounts', 'Sales'],
  },
  {
    label: 'Payments',
    path: '/payments',
    icon: 'payments',
    allowedRoles: ['Admin', 'Accounts'],
  },
  {
    label: 'Inventory',
    path: '/inventory',
    icon: 'inventory_2',
    allowedRoles: ['Admin', 'Operations'],
  },
  {
    label: 'Reports',
    path: '/reports',
    icon: 'assessment',
    allowedRoles: ['Admin', 'Operations', 'Accounts'],
  },
  {
    label: 'Master Data',
    path: '/master-data',
    icon: 'database',
    allowedRoles: ['Admin'],
  },
];

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);
  const helpRef = useRef<HTMLDivElement>(null);
  const { user, logout, role } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  // Close dropdowns on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) setNotifOpen(false);
      if (helpRef.current && !helpRef.current.contains(e.target as Node)) setHelpOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const userFullName = user ? `${user.first_name} ${user.last_name}` : '';
  const userInitials = user
    ? `${user.first_name.charAt(0)}${user.last_name.charAt(0)}`
    : '';

  const filteredNavItems = navItems.filter(
    (item) => role && item.allowedRoles.includes(role),
  );

  const isActive = (path: string) =>
    location.pathname === path || location.pathname.startsWith(path + '/');

  return (
    <div className="min-h-screen bg-surface-variant">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/30 lg:hidden"
          onClick={() => { setSidebarOpen(false); }}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed top-0 left-0 z-50 h-full w-60 bg-surface border-r border-outline flex flex-col transition-transform duration-200 lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* App branding */}
        <div className="flex items-center gap-3 px-5 py-5 border-b border-outline-variant">
          <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center">
            <span className="material-symbols-outlined text-on-primary text-lg">
              conveyor_belt
            </span>
          </div>
          <div>
            <p className="text-title-md text-on-surface font-semibold leading-tight">
              Logistics ERP
            </p>
            <p className="text-body-sm text-on-surface-variant">Enterprise Freight</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {filteredNavItems.map((item) => {
            const active = isActive(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => { setSidebarOpen(false); }}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-body-lg transition-colors no-underline ${
                  active
                    ? 'bg-secondary-container text-on-secondary-container font-semibold'
                    : 'text-on-surface-variant hover:bg-surface-variant'
                }`}
              >
                <span className="material-symbols-outlined text-[20px]">
                  {item.icon}
                </span>
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* New Booking button */}
        {role && ['Admin', 'Operations'].includes(role) && (
          <div className="px-4 pb-4">
            <Link
              to="/bookings/new"
              onClick={() => { setSidebarOpen(false); }}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-primary text-on-primary rounded-xl font-medium text-body-md hover:bg-primary/90 transition-colors no-underline"
            >
              <span className="material-symbols-outlined text-[18px]">add</span>
              New Booking
            </Link>
          </div>
        )}
      </aside>

      {/* Header */}
      <header className="fixed top-0 right-0 left-0 lg:left-60 z-30 h-16 bg-surface border-b border-outline flex items-center justify-between px-4 gap-4">
        {/* Left: Mobile menu + Search */}
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {/* Mobile menu toggle */}
          <button
            className="lg:hidden p-2 rounded-lg hover:bg-surface-variant text-on-surface-variant flex-shrink-0"
            onClick={() => { setSidebarOpen(true); }}
            aria-label="Open navigation menu"
          >
            <span className="material-symbols-outlined">menu</span>
          </button>

          {/* Search input */}
          <div className="flex-1 max-w-md relative">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">
              search
            </span>
            <input
              type="text"
              placeholder="Search bookings, clients, job numbers..."
              className="w-full pl-10 pr-4 py-2 rounded-full bg-surface-variant border border-outline-variant text-body-md text-on-surface placeholder:text-on-surface-variant/60 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-colors"
            />
          </div>
        </div>

        {/* Right side icons + user */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Notification icon with dropdown */}
          <div className="relative" ref={notifRef}>
            <button
              onClick={() => { setNotifOpen(!notifOpen); setHelpOpen(false); }}
              className="p-2 rounded-lg hover:bg-surface-variant text-on-surface-variant relative"
              aria-label="Notifications"
            >
              <span className="material-symbols-outlined text-[22px]">notifications</span>
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-error rounded-full" />
            </button>
            {notifOpen && (
              <div className="absolute right-0 top-full mt-2 w-80 bg-surface rounded-xl border border-outline-variant shadow-lg z-50 overflow-hidden">
                <div className="px-4 py-3 border-b border-outline-variant">
                  <p className="text-title-sm font-semibold text-on-surface">Notifications</p>
                </div>
                <div className="max-h-64 overflow-y-auto">
                  <div className="px-4 py-3 hover:bg-surface-variant/50 border-b border-outline-variant/50">
                    <p className="text-body-sm text-on-surface font-medium">Payment overdue</p>
                    <p className="text-body-sm text-on-surface-variant">Check pending payments in dashboard</p>
                  </div>
                  <div className="px-4 py-3 hover:bg-surface-variant/50 border-b border-outline-variant/50">
                    <p className="text-body-sm text-on-surface font-medium">BL pending submission</p>
                    <p className="text-body-sm text-on-surface-variant">Review draft BLs for active bookings</p>
                  </div>
                  <div className="px-4 py-3 hover:bg-surface-variant/50">
                    <p className="text-body-sm text-on-surface font-medium">Low stock alert</p>
                    <p className="text-body-sm text-on-surface-variant">Some inventory items are running low</p>
                  </div>
                </div>
                <div className="px-4 py-2 border-t border-outline-variant">
                  <button
                    onClick={() => { navigate('/dashboard'); setNotifOpen(false); }}
                    className="text-body-sm text-primary font-medium hover:underline"
                  >
                    View all alerts →
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Help icon with modal */}
          <div className="relative" ref={helpRef}>
            <button
              onClick={() => { setHelpOpen(!helpOpen); setNotifOpen(false); }}
              className="p-2 rounded-lg hover:bg-surface-variant text-on-surface-variant"
              aria-label="Help"
            >
              <span className="material-symbols-outlined text-[22px]">help</span>
            </button>
            {helpOpen && (
              <div className="absolute right-0 top-full mt-2 w-72 bg-surface rounded-xl border border-outline-variant shadow-lg z-50 overflow-hidden">
                <div className="px-4 py-3 border-b border-outline-variant">
                  <p className="text-title-sm font-semibold text-on-surface">Help & Support</p>
                </div>
                <div className="p-4 space-y-3">
                  <div className="flex items-center gap-3">
                    <span className="material-symbols-outlined text-primary text-[20px]">mail</span>
                    <div>
                      <p className="text-body-sm text-on-surface font-medium">Email Support</p>
                      <p className="text-body-sm text-on-surface-variant">support@parthsudra.com</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="material-symbols-outlined text-primary text-[20px]">call</span>
                    <div>
                      <p className="text-body-sm text-on-surface font-medium">Phone</p>
                      <p className="text-body-sm text-on-surface-variant">Contact administrator</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="material-symbols-outlined text-primary text-[20px]">info</span>
                    <div>
                      <p className="text-body-sm text-on-surface font-medium">Version</p>
                      <p className="text-body-sm text-on-surface-variant">Logistics ERP v1.0</p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Divider */}
          <div className="w-px h-8 bg-outline-variant mx-1 hidden sm:block" />

          {/* User info */}
          <div className="hidden sm:flex items-center gap-2">
            <button
              onClick={() => navigate('/profile')}
              className="flex items-center gap-2 px-2 py-1 rounded-xl hover:bg-surface-variant transition-colors"
              aria-label="View profile"
            >
              <div className="text-right">
                <p className="text-body-md text-on-surface font-medium leading-tight">
                  {userFullName}
                </p>
                <p className="text-body-sm text-on-surface-variant">{role}</p>
              </div>
              {user?.avatar_url ? (
                <img
                  src={user.avatar_url}
                  alt="User avatar"
                  className="w-9 h-9 rounded-full object-cover"
                />
              ) : (
                <div className="w-9 h-9 rounded-full bg-primary-container text-on-primary-container flex items-center justify-center text-label-lg font-semibold">
                  {userInitials}
                </div>
              )}
            </button>
          </div>

          {/* Logout */}
          <button
            onClick={logout}
            className="p-2 rounded-lg hover:bg-error-container text-on-surface-variant hover:text-error transition-colors"
            aria-label="Logout"
            title="Logout"
          >
            <span className="material-symbols-outlined text-[22px]">logout</span>
          </button>
        </div>
      </header>

      {/* Main content */}
      <main className="lg:ml-60 pt-16 min-h-screen">
        <div className="p-6">{children}</div>
      </main>
    </div>
  );
}
