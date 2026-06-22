# Implementation Plan: React Frontend

## Overview

This plan implements a React SPA for the logistics ERP platform, served via Nginx at the root path while proxying API requests to the Django backend. The implementation follows a bottom-up dependency order: project scaffolding → foundation (API client, token store) → auth → routing → layout → feature views → deployment configuration → property-based tests.

## Tasks

- [x] 1. Project scaffolding and core configuration
  - [x] 1.1 Initialize Vite + React + TypeScript project in `frontend/` directory
    - Run `npm create vite@latest frontend -- --template react-ts`
    - Install dependencies: `react-router-dom`, `@tanstack/react-query`, `react-hook-form`, `@hookform/resolvers`, `zod`, `@mui/material`, `@emotion/react`, `@emotion/styled`, `axios`
    - Install dev dependencies: `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`, `fast-check`, `msw`, `jsdom`
    - Configure `vite.config.ts` with proxy for `/api/` in development mode
    - Configure `tsconfig.json` with strict mode and path aliases
    - Configure `vitest.config.ts` with jsdom environment and setup files
    - Create the folder structure as defined in the design (src/api/, src/auth/, src/router/, src/features/, src/components/, src/utils/)
    - _Requirements: 12.1, 12.2_

- [x] 2. API client and token store (foundation layer)
  - [x] 2.1 Implement in-memory token store (`src/auth/tokenStore.ts`)
    - Create module-scoped variables for access and refresh tokens (closure-based)
    - Implement `getAccessToken()`, `getRefreshToken()`, `setTokens(access, refresh)`, `clearTokens()` functions
    - Ensure no interaction with localStorage or sessionStorage
    - _Requirements: 1.4, 1.8_

  - [x] 2.2 Implement Axios API client with interceptors (`src/api/client.ts`)
    - Create Axios instance with baseURL set to `/api/`
    - Add request interceptor to attach Bearer token from token store on every request
    - Add response interceptor to handle 401: attempt refresh exactly once via POST `/api/accounts/token/refresh/`, queue concurrent requests behind the refresh promise, retry original request on success, clear tokens and redirect to login on failure
    - Define API endpoint constants in `src/api/endpoints.ts`
    - Define shared API response types in `src/api/types.ts` (PaginatedResponse, error shapes)
    - _Requirements: 1.4, 1.5, 1.6_

- [x] 3. Authentication module
  - [x] 3.1 Implement AuthProvider and useAuth hook (`src/auth/AuthProvider.tsx`, `src/auth/useAuth.ts`)
    - Create AuthContext with `user`, `isAuthenticated`, `login()`, `logout()`, `role` fields
    - `login()` sends POST to `/api/accounts/token/` with username/password, stores tokens via tokenStore, fetches user profile from `/api/accounts/users/me/`
    - `logout()` clears tokens and redirects to login page
    - Define auth types in `src/auth/types.ts` (User, Role, AuthContextValue)
    - _Requirements: 1.1, 1.2, 1.3, 1.6, 1.7_

  - [x] 3.2 Implement Login page (`src/features/auth/LoginPage.tsx`)
    - Build login form with username and password fields using React Hook Form + Zod validation
    - Display client-side validation errors for empty fields before submission
    - Display server-side authentication failure error without revealing which field is wrong
    - On success, redirect to stored return path or dashboard
    - _Requirements: 1.1, 1.2, 1.3_

- [x] 4. Router and role-based guards
  - [x] 4.1 Implement route definitions and role guard (`src/router/routes.tsx`, `src/router/RoleGuard.tsx`, `src/router/routePermissions.ts`)
    - Define route permission mapping (role → allowed paths) as specified in design
    - Implement `RoleGuard` component that checks authentication status and role permissions
    - Redirect unauthenticated users to login while storing the intended path for post-login redirect
    - Display unauthorized access message with Dashboard link for authenticated users without route permission (do NOT log out)
    - Wire routes into App.tsx with React Router v6 layout nesting
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8_

- [x] 5. Layout and navigation shell
  - [x] 5.1 Implement responsive layout with sidebar (`src/components/Layout.tsx`, `src/components/Sidebar.tsx`)
    - Build persistent sidebar for desktop viewports (≥1024px) with role-filtered navigation links
    - Implement hamburger menu toggle for viewports <1024px that closes on link selection
    - Display user's full name and role label in navigation header
    - Highlight active navigation link based on current route
    - _Requirements: 11.1, 11.2, 11.3, 11.5_

  - [x] 5.2 Implement global loading indicator and error boundary (`src/components/LoadingIndicator.tsx`, `src/components/ErrorBoundary.tsx`)
    - Build thin progress bar (top of viewport) that appears after 300ms of pending API requests
    - Remove indicator within 100ms of response
    - Implement top-level ErrorBoundary for unhandled React errors
    - _Requirements: 11.4_

- [x] 6. Checkpoint
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Dashboard view
  - [x] 7.1 Implement Dashboard page with role-specific data (`src/features/dashboard/DashboardPage.tsx`, `src/features/dashboard/useDashboardData.ts`)
    - Fetch dashboard counts from API (no caching — `staleTime: 0` in TanStack Query)
    - Render Operations dashboard: PENDING count, DO_BOOKING_EDIT count, upcoming ETD count (next 7 days)
    - Render Admin dashboard: same as Operations + Master Data navigation link
    - Render Accounts dashboard: PENDING count + recent report exports count (last 7 days)
    - Render Sales dashboard: PENDING and DO_BOOKING_EDIT counts filtered by user's marketing_person
    - Handle missing MarketingPerson profile (display zero counts + info message)
    - Handle API failure (display error message + retry action)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

- [x] 8. Booking form and sub-forms
  - [x] 8.1 Implement Zod validation schemas (`src/features/bookings/schema.ts`)
    - Create `bookingSchema` with all mandatory fields, conditional HAZ validation, and date ordering refinements
    - Create `containerSchema` with type, size enum, count min, and string length constraints
    - Create `transhipmentLegSchema` with etd > eta refinement
    - Create `transhipmentLegsSchema` array with max(4) and chronological ordering validation
    - _Requirements: 4.1, 4.8, 5.2, 5.3, 6.2, 6.3_

  - [x] 8.2 Implement Booking form page (`src/features/bookings/BookingFormPage.tsx`, `src/features/bookings/useBookingForm.ts`)
    - Build form with React Hook Form + Zod resolver for the booking schema
    - Mark mandatory fields with asterisk indicator
    - Organize optional fields into logical sections (Voyage & Schedule, Cut-off Dates, etc.)
    - Populate foreign-key dropdowns from `/api/master-data/{entity_type}/?is_active=true`
    - Handle dropdown load failure (inline error + disable field)
    - Show/hide HAZ fields based on `is_haz` toggle
    - Submit via POST (create) or PATCH (edit), navigate to detail on success
    - Map API 400 validation errors to form field positions, preserve all entered data
    - Pre-populate form from GET `/api/bookings/{id}/` when editing
    - Handle GET failure on edit (error message + retry, no navigation away)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10_

  - [x] 8.3 Implement Container sub-form (`src/features/bookings/components/ContainerSubForm.tsx`, `src/features/bookings/useContainers.ts`)
    - Build repeatable container entry section within booking form (max 50 entries)
    - Fields: container_type (dropdown), container_size (enum select), container_count (number), container_no (text, max 20), seal_no (text, max 20)
    - POST to `/api/bookings/{id}/containers/` on save (single or array)
    - DELETE to `/api/bookings/{id}/containers/{cid}/` on remove
    - Load existing containers from GET when editing
    - Display validation errors from API (400) inline
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9_

  - [x] 8.4 Implement Transhipment sub-form (`src/features/bookings/components/TranshipmentSubForm.tsx`, `src/features/bookings/useTranshipments.ts`)
    - Build repeatable transhipment leg section (max 4 legs)
    - Fields: port (dropdown, active ports only), eta (datetime), connecting_vessel_voyage (text, max 200), etd (datetime)
    - Client-side validation: etd > eta per leg, chronological ordering between legs
    - POST to `/api/bookings/{id}/transhipments/` with legs array on save
    - PUT to `/api/bookings/{id}/transhipments/{lid}/` on update (re-validate ordering)
    - DELETE to `/api/bookings/{id}/transhipments/{lid}/` and re-display remaining legs
    - Disable add button when 4 legs exist
    - Load existing legs from GET in sequence order when editing
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9_

  - [x] 8.5 Implement Notification history section (`src/features/bookings/components/NotificationHistory.tsx`)
    - Display communication logs from booking detail response
    - Show email_type, recipients, sent_at, status per entry
    - Style failed entries with visually distinct warning (red)
    - Display "Pending" when sent_at is null
    - Sort by created_at descending
    - Show "No notifications sent yet" message when empty
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

- [x] 9. Search view
  - [x] 9.1 Implement Search page (`src/features/search/SearchPage.tsx`, `src/features/search/useBookingSearch.ts`)
    - Build text search input querying `/api/bookings/search/?q=` (1–100 chars, do not fire for empty or >100)
    - Display results in paginated table (default 25, max 100 rows): job_number, client, shipping_line, pol, pod, status, booking_date (sorted descending)
    - Row click navigates to booking detail/edit
    - Filter controls: status (multi-select), shipping_line (dropdown), date range
    - Hide create/edit actions for Accounts role
    - Display "No bookings match" message on empty results (preserve search input)
    - Display error message + retry on API failure
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_

- [x] 10. Reports view
  - [x] 10.1 Implement Reports page (`src/features/reports/ReportsPage.tsx`, `src/features/reports/useReports.ts`)
    - Build tabbed interface: Pending DO Report and Master Report
    - Pending DO: fetch from `/api/reports/pending-do/` with filters (client, vessel_voyage, date range, shipping_line), default last 30 days
    - Master Report: fetch from `/api/reports/master/` with filters (client, vessel_voyage, date range, status, shipping_line), default last 90 days
    - Display paginated table (50 rows per page)
    - Export button triggers download from `/api/reports/{type}/export/?format=csv` or `format=excel`
    - Display "No data found" on empty results
    - Restrict access to Operations and Admin roles
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9_

- [x] 11. Master data management view
  - [x] 11.1 Implement Master Data page (`src/features/master-data/MasterDataPage.tsx`, `src/features/master-data/useMasterData.ts`)
    - Build entity type navigation listing all 12 entity types
    - Display paginated entity table (default 25, max 100) with name-based search filter
    - "Add New" form with entity-specific fields, required name (max 255, unique), POST on submit
    - "Edit" pre-populated form, PATCH on submit
    - Toggle active status via PATCH is_active
    - Display validation errors (duplicate name, blank name) inline
    - Handle 409 Conflict on delete (entity in use message)
    - Admin-only access enforced client-side (role guard) and server-side (403)
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9_

- [x] 12. Checkpoint
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Deployment configuration
  - [x] 13.1 Create frontend Dockerfile (multi-stage build)
    - Stage 1 (build): Node 20 alpine, install deps, run `npm run build`, output to `/app/build`
    - Stage 2 (serve): nginx:alpine, copy build output to `/usr/share/nginx/html`
    - _Requirements: 12.1, 12.3_

  - [x] 13.2 Update Nginx configuration (`nginx/nginx.conf`)
    - Route `/api/` and `/admin/` to Django upstream (proxy_pass)
    - Serve `/static/` from Django staticfiles volume
    - Serve all other paths from React build directory with `try_files $uri $uri/ /index.html` fallback for SPA routing
    - Preserve existing SSL configuration and server_name
    - _Requirements: 12.4_

  - [x] 13.3 Update `docker-compose.yml` to integrate frontend build
    - Replace or update the `nginx` service to build from `frontend/Dockerfile` (multi-stage produces nginx image with React assets baked in)
    - Mount `nginx/nginx.conf` as the site config
    - Mount `static_volume` for Django static files
    - Mount Let's Encrypt certs volume
    - Ensure the frontend container depends on the `web` service
    - _Requirements: 12.2, 12.3, 12.4_

- [x] 14. Property-based tests
  - [x]* 14.1 Write property test: Bearer Token Attachment Invariant
    - **Property 1: Bearer Token Attachment Invariant**
    - Generate arbitrary HTTP method, URL path, and request body; verify that when a token is in the store, the request interceptor attaches it as a Bearer header
    - **Validates: Requirements 1.4**

  - [x]* 14.2 Write property test: Token Storage Exclusion
    - **Property 2: Token Storage Exclusion**
    - Generate arbitrary token strings (unicode, special chars); after `setTokens()`, assert localStorage and sessionStorage do not contain the token value in any key
    - **Validates: Requirements 1.8**

  - [x]* 14.3 Write property test: Protected Route Redirect Preservation
    - **Property 3: Protected Route Redirect Preservation**
    - Generate valid protected route paths from the permissions list; in unauthenticated state, verify redirect to login stores the path and post-login navigates back
    - **Validates: Requirements 2.1, 2.2**

  - [x]* 14.4 Write property test: Role-Route Access Denial Without Logout
    - **Property 4: Role-Route Access Denial Without Logout**
    - Generate (Role, Route) pairs where the route is NOT in the role's allowed set; verify unauthorized message is shown, Dashboard link exists, and auth state is preserved
    - **Validates: Requirements 2.3**

  - [x]* 14.5 Write property test: Validation Error Field Mapping
    - **Property 5: Validation Error Field Mapping**
    - Generate random subsets of booking form field names as error keys in a 400 response; verify each error is displayed adjacent to its field and all form values are preserved
    - **Validates: Requirements 4.7**

  - [x]* 14.6 Write property test: Booking Date Ordering Validation
    - **Property 6: Booking Date Ordering Validation**
    - Generate random date pairs; verify schema produces error on booking_validity_date when booking_date > booking_validity_date, error on forwarding_window_end when start > end, and no error when both constraints satisfied
    - **Validates: Requirements 4.8**

  - [x]* 14.7 Write property test: Container Entry Schema Validation
    - **Property 7: Container Entry Schema Validation**
    - Generate random container objects with varying types, sizes, counts, and string lengths; verify schema rejects invalid entries and accepts valid ones
    - **Validates: Requirements 5.2, 5.3**

  - [x]* 14.8 Write property test: Transhipment Leg Chronological Validation
    - **Property 8: Transhipment Leg Chronological Validation**
    - Generate arrays of 1–4 legs with random datetime values; verify schema fails when etd ≤ eta or chronological order violated, passes when all constraints satisfied
    - **Validates: Requirements 6.3**

  - [x]* 14.9 Write property test: Search Query Length Gating
    - **Property 9: Search Query Length Gating**
    - Generate random strings of length 0–150; verify API request is dispatched only for strings with length 1–100
    - **Validates: Requirements 7.1**

- [x] 15. Final checkpoint
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The frontend is a NEW project — `frontend/` directory does not exist yet
- All API paths are relative (`/api/`) so Nginx proxying works on the same domain
- MSW should be set up for API mocking in tests as part of task 1.1 vitest configuration

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1"] },
    { "id": 2, "tasks": ["2.2"] },
    { "id": 3, "tasks": ["3.1", "3.2"] },
    { "id": 4, "tasks": ["4.1"] },
    { "id": 5, "tasks": ["5.1", "5.2"] },
    { "id": 6, "tasks": ["7.1", "8.1"] },
    { "id": 7, "tasks": ["8.2", "9.1", "10.1", "11.1"] },
    { "id": 8, "tasks": ["8.3", "8.4", "8.5"] },
    { "id": 9, "tasks": ["13.1", "13.2"] },
    { "id": 10, "tasks": ["13.3"] },
    { "id": 11, "tasks": ["14.1", "14.2", "14.6", "14.7", "14.8", "14.9"] },
    { "id": 12, "tasks": ["14.3", "14.4", "14.5"] }
  ]
}
```
