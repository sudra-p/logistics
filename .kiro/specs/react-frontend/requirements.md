# Requirements Document

## Introduction

This document defines the requirements for a React-based frontend application for the logistics ERP platform at erp.parthsudra.com. The frontend consumes the existing Django REST Framework API (JWT-authenticated) and provides role-based views for booking management, reporting, master data administration, and communication history. The React app is served as a static build via Nginx at the root path (/) while the API remains at /api/.

## Glossary

- **Frontend_App**: The React single-page application served as static assets via Nginx
- **Auth_Module**: The authentication subsystem responsible for JWT token management (login, refresh, logout)
- **Dashboard_View**: The landing page shown after login, displaying role-specific summary information
- **Booking_Form**: The form component for creating and editing sea-export forwarding bookings
- **Container_SubForm**: The nested form section for managing container allocations within a booking
- **Transhipment_SubForm**: The nested form section for managing transhipment routing legs within a booking
- **Search_View**: The search and filter interface used by Customer Service / Operations staff to find bookings
- **Reports_View**: The reporting interface showing tabular data with filtering and export capabilities
- **MasterData_View**: The admin interface for CRUD operations on master data entities
- **Notification_View**: The interface displaying email communication history for bookings
- **API_Client**: The HTTP client layer that handles requests to the backend, including token attachment and refresh logic
- **Router**: The client-side routing module that maps URL paths to views and enforces access control
- **Role**: One of four user groups (Admin, Operations, Accounts, Sales) that determines accessible views and actions
- **Access_Token**: A short-lived JWT (60-minute expiry) used to authenticate API requests
- **Refresh_Token**: A longer-lived JWT (7-day expiry) used to obtain new access tokens without re-login

## Requirements

### Requirement 1: JWT Authentication

**User Story:** As a user, I want to log in with my credentials and have the app manage my session automatically, so that I can access the system securely without repeated logins.

#### Acceptance Criteria

1. WHEN a user submits a valid username and password on the login page, THE Auth_Module SHALL send a POST request to /api/accounts/token/ with the username and password fields in the request body and store the returned access and refresh tokens in memory
2. WHEN a user submits invalid credentials, THE Auth_Module SHALL display an error message indicating authentication failure without revealing whether the username or password was incorrect
3. IF the user submits the login form with the username or password field empty, THEN THE Auth_Module SHALL display a validation error indicating which field is required without sending a request to the server
4. WHILE an Access_Token is present in memory, THE API_Client SHALL attach the token as a Bearer authorization header on all API requests
5. WHEN an API request returns a 401 status, THE API_Client SHALL attempt to refresh the Access_Token exactly once using the Refresh_Token via POST /api/accounts/token/refresh/ and queue any concurrent API requests until the refresh completes or fails
6. IF the token refresh request fails, THEN THE Auth_Module SHALL clear all stored tokens and redirect the user to the login page
7. WHEN a user clicks the logout button, THE Auth_Module SHALL clear all stored tokens from memory and redirect to the login page
8. THE Auth_Module SHALL NOT store tokens in localStorage or sessionStorage to mitigate XSS attack vectors

### Requirement 2: Client-Side Routing and Role-Based Access

**User Story:** As a system administrator, I want the frontend to enforce role-based navigation, so that users only see views relevant to their permissions.

#### Acceptance Criteria

1. THE Router SHALL define protected routes that require an Access_Token to be present in memory before rendering the target view
2. WHEN an unauthenticated user navigates to a protected route, THE Router SHALL store the requested path and redirect the user to the login page, and after successful login THE Router SHALL redirect the user to the originally requested path
3. WHEN an authenticated user navigates to a route their Role does not permit, THE Router SHALL display a message indicating unauthorized access and provide a navigation link back to the Dashboard_View without logging the user out
4. THE Router SHALL determine the user's Role from the authenticated user profile and evaluate route permissions on each navigation event
5. THE Router SHALL grant Admin role access to all views including MasterData_View
6. THE Router SHALL grant Operations role access to Dashboard_View, Booking_Form, Search_View, Reports_View, and Notification_View
7. THE Router SHALL grant Accounts role access to Dashboard_View, Search_View, and Reports_View, where Search_View SHALL hide create and edit action controls and restrict navigation to the Booking_Form
8. THE Router SHALL grant Sales role access to Dashboard_View and Search_View, where Search_View data filtering to the user's associated bookings is enforced server-side via the API

### Requirement 3: Dashboard View

**User Story:** As a logged-in user, I want to see a summary dashboard relevant to my role after login, so that I can quickly assess pending work.

#### Acceptance Criteria

1. WHEN an Operations user accesses the Dashboard_View, THE Frontend_App SHALL display a count of bookings with status PENDING, a count of bookings with status DO_BOOKING_EDIT, and a count of bookings with etd_pol within the next 7 calendar days from the current date
2. WHEN an Admin user accesses the Dashboard_View, THE Frontend_App SHALL display the same three counts as the Operations dashboard plus a navigation link to the MasterData_View
3. WHEN an Accounts user accesses the Dashboard_View, THE Frontend_App SHALL display a count of bookings with status PENDING and a count of report exports (Pending DO or Master) performed by any user within the last 7 calendar days
4. WHEN a Sales user accesses the Dashboard_View, THE Frontend_App SHALL display counts of bookings with status PENDING and DO_BOOKING_EDIT where the booking's marketing_person is linked to the logged-in user's MarketingPerson profile
5. WHEN the Dashboard_View page is visited or navigated to, THE Frontend_App SHALL fetch fresh counts from the API without using cached responses from previous visits
6. IF the Sales user does not have an associated MarketingPerson profile, THEN THE Frontend_App SHALL display zero counts and an informational message indicating no marketing person profile is linked to their account
7. IF the dashboard data API request fails, THEN THE Frontend_App SHALL display an error message indicating the counts could not be loaded and provide a retry action

### Requirement 4: Booking Entry Form

**User Story:** As an Operations user, I want to create and edit bookings through a structured form, so that I can capture all shipment details accurately.

#### Acceptance Criteria

1. THE Booking_Form SHALL present all mandatory fields (booking_date, booking_validity_date, forwarding_window_start, forwarding_window_end, shipping_line, pol, pod, client, commodity, cargo_type, shipment_type, stuffing_type) with an asterisk (*) symbol adjacent to each field label as the required-field indicator
2. THE Booking_Form SHALL present optional fields organized into logical sections: Voyage & Schedule, Cut-off Dates, Clearance & Stuffing, Parties, Documentation, Certificates (maximum 5 entries), and HAZ Details
3. WHEN a user selects is_haz as true, THE Booking_Form SHALL display haz_class, haz_uin, and haz_group fields as conditionally required with the same asterisk (*) required-field indicator
4. THE Booking_Form SHALL populate all foreign-key dropdown fields (shipping_line, pol, pod, client, commodity, vessel, transporter, marketing_person, nvocc_forwarder, shipper, consignee, por, fpd) by fetching entities with is_active=true from /api/master-data/{entity_type}/
5. IF the master-data dropdown fetch for a field fails, THEN THE Booking_Form SHALL display an inline error message indicating the data could not be loaded and disable the affected dropdown field until the user retries
6. WHEN the user submits the form with valid data, THE Booking_Form SHALL send a POST request to /api/bookings/ and navigate to the booking detail view on success
7. WHEN the API returns validation errors on submission, THE Booking_Form SHALL display each error message adjacent to the corresponding field and preserve all user-entered form data without clearing any fields
8. THE Booking_Form SHALL validate date ordering client-side (booking_date ≤ booking_validity_date, forwarding_window_start ≤ forwarding_window_end) before submission, and display an inline error message below the violating date field indicating the required ordering constraint
9. WHEN editing an existing booking, THE Booking_Form SHALL pre-populate all fields from a GET /api/bookings/{id}/ response and submit changes via PATCH
10. IF the GET /api/bookings/{id}/ request fails when loading the edit form, THEN THE Booking_Form SHALL display an error message indicating the booking could not be loaded and provide a retry option without navigating away from the current view

### Requirement 5: Container Sub-Form

**User Story:** As an Operations user, I want to add, edit, and remove container allocations within a booking, so that I can specify cargo details.

#### Acceptance Criteria

1. THE Container_SubForm SHALL display within the Booking_Form as a repeatable section allowing addition of up to 50 container entries per booking
2. WHEN a user adds a container entry, THE Container_SubForm SHALL require container_type (from master data dropdown), container_size (20FT, 40FT, 40FT_HC, 45FT), and container_count (integer, minimum 1)
3. THE Container_SubForm SHALL provide optional fields for container_no (maximum 20 characters) and seal_no (maximum 20 characters) per entry
4. WHEN the user saves container entries, THE Container_SubForm SHALL send a POST request to /api/bookings/{id}/containers/ accepting either a single object or a list of objects, and return the created container records with HTTP 201 on success
5. WHEN the user removes a container entry, THE Container_SubForm SHALL send a DELETE request to /api/bookings/{id}/containers/{container_id}/ and return HTTP 204 on success
6. WHEN editing a booking, THE Container_SubForm SHALL display existing containers fetched from GET /api/bookings/{id}/containers/ and display an empty list when no containers exist
7. IF the user submits a container entry with an invalid container_size, a non-existent container_type, or a container_count less than 1, THEN THE Container_SubForm SHALL reject the request with HTTP 400 and return a response indicating which field failed validation
8. IF adding container entries would exceed 50 total entries for the booking, THEN THE Container_SubForm SHALL reject the request with HTTP 400 and return a response indicating the maximum limit has been reached
9. IF the specified booking or container does not exist, THEN THE Container_SubForm SHALL return HTTP 404

### Requirement 6: Transhipment Sub-Form

**User Story:** As an Operations user, I want to define transhipment routing legs for multi-port shipments, so that I can track cargo through intermediate ports.

#### Acceptance Criteria

1. THE Transhipment_SubForm SHALL display within the Booking_Form as a repeatable section allowing up to 4 transhipment legs
2. WHEN a user adds a transhipment leg, THE Transhipment_SubForm SHALL require port (from master data dropdown, limited to active ports), eta (datetime), connecting_vessel_voyage (free text, maximum 200 characters), and etd (datetime) fields
3. THE Transhipment_SubForm SHALL validate that etd is strictly after eta for each leg, and that legs are in chronological order where each subsequent leg's eta is equal to or after the previous leg's etd, before submission
4. WHEN the user saves transhipment legs, THE Transhipment_SubForm SHALL send a POST request to /api/bookings/{id}/transhipments/ with a legs array containing the leg data
5. IF transhipment leg validation fails (etd not after eta, chronological order violated, more than 4 total legs, or missing required fields), THEN THE Transhipment_SubForm SHALL display a validation error message indicating the specific failure and preserve the user's entered data without saving
6. THE Transhipment_SubForm SHALL enforce a maximum of 4 legs (including any existing legs) by disabling the add button when 4 legs exist
7. THE Transhipment_SubForm SHALL display existing transhipment legs fetched from GET /api/bookings/{id}/transhipments/ in sequence order when editing a booking
8. WHEN the user deletes a transhipment leg, THE Transhipment_SubForm SHALL send a DELETE request to /api/bookings/{id}/transhipments/{leg_id}/ and re-display the remaining legs with updated sequence numbers starting from 1
9. WHEN the user updates a transhipment leg, THE Transhipment_SubForm SHALL send a PUT request to /api/bookings/{id}/transhipments/{leg_id}/ with the full leg data (port, eta, connecting_vessel_voyage, etd) and re-validate chronological ordering against adjacent legs

### Requirement 7: Search and Filter View

**User Story:** As a Customer Service / Operations user, I want to search and filter bookings, so that I can quickly locate specific shipments.

#### Acceptance Criteria

1. THE Search_View SHALL provide a text search input that queries /api/bookings/search/?q= supporting job_number, booking_no, client name, hbl_no, and mbl_no, where the search query must be between 1 and 100 characters in length and performs a case-insensitive partial match against any of the supported fields
2. THE Search_View SHALL display results in a paginated table (default 25 rows per page, maximum 100 rows per page) showing job_number, client, shipping_line, pol, pod, status, and booking_date columns, sorted by booking_date descending
3. WHEN a user clicks a row in the results table, THE Search_View SHALL navigate to the booking detail or edit view for the selected booking
4. THE Search_View SHALL provide filter controls for status (matching values: PENDING, DO_BOOKING_EDIT, COMPLETED), shipping_line (selectable from active shipping lines), and booking_date range (start date and end date, where start date must not be after end date)
5. WHEN a Sales user accesses the Search_View, THE Frontend_App SHALL only display bookings associated with the Sales user's marketing person profile (enforced server-side via queryset filtering)
6. IF the search query returns no matching results, THEN THE Search_View SHALL display a message indicating that no bookings match the search criteria and retain the current search input and filter selections
7. IF the search or filter API request fails, THEN THE Search_View SHALL display an error message indicating that results could not be loaded and allow the user to retry the request

### Requirement 8: Reports View

**User Story:** As an Operations or Admin user, I want to view and export tabular reports, so that I can analyze booking data and share it with stakeholders.

#### Acceptance Criteria

1. THE Reports_View SHALL present two report tabs: Pending DO Report and Master Report
2. WHEN the Pending DO tab is selected, THE Reports_View SHALL fetch data from /api/reports/pending-do/ with support for client, vessel_voyage, booking_date_from, booking_date_to, and shipping_line filters
3. WHEN the Master Report tab is selected, THE Reports_View SHALL fetch data from /api/reports/master/ with support for client, vessel_voyage, created_date_from, created_date_to, status, and shipping_line filters
4. THE Reports_View SHALL display report data in a paginated table with 50 rows per page
5. WHEN the user clicks an export button, THE Reports_View SHALL trigger a download by calling /api/reports/{report_type}/export/?format=csv or format=excel, with exports capped at 50,000 rows
6. THE Reports_View SHALL display a "No data found" message when the API returns an empty results array
7. IF no date range filters are provided for the Pending DO report, THEN THE Reports_View SHALL default to showing data from the last 30 days based on booking_date; IF no date range filters are provided for the Master Report, THEN THE Reports_View SHALL default to showing data from the last 90 days based on created_date
8. IF the export format query parameter is missing or is not one of "csv" or "excel", THEN THE Reports_View SHALL return an error response indicating that a valid format parameter is required
9. THE Reports_View SHALL restrict access to users with Operations or Admin roles, returning an unauthorized error for all other users

### Requirement 9: Master Data Management

**User Story:** As an Admin user, I want to manage master data entities (clients, ports, vessels, etc.), so that the system's reference data stays current.

#### Acceptance Criteria

1. THE MasterData_View SHALL present a navigation listing all entity types: Client, Consignee, Shipper, Broker, ShippingLine, Vessel, Port, Commodity, ContainerType, MarketingPerson, Transporter, Forwarder
2. WHEN an entity type is selected, THE MasterData_View SHALL display a paginated table of entities fetched from GET /api/master-data/{entity_type}/ with a default page size of 25 items, a maximum page size of 100 items, and support for name-based filtering via a search query parameter
3. WHEN the Admin clicks "Add New", THE MasterData_View SHALL display a form with fields specific to the selected entity type including a required name field (maximum 255 characters, unique per entity type) and submit via POST /api/master-data/{entity_type}/
4. WHEN the Admin clicks "Edit" on a row, THE MasterData_View SHALL display a pre-populated form and submit changes via PATCH /api/master-data/{entity_type}/{id}/
5. WHEN the Admin toggles an entity's active status, THE MasterData_View SHALL send a PATCH request updating is_active and update the entity's displayed status in the table upon a successful response
6. IF a non-Admin user attempts to create, update, or delete a master data entity, THEN THE System SHALL reject the request with a 403 Forbidden status and preserve the entity unchanged
7. IF the Admin submits a form with a name that already exists for that entity type or with a blank name, THEN THE MasterData_View SHALL display a validation error message indicating the specific field failure without saving the entity
8. IF the Admin attempts to delete an entity that is referenced by existing booking records, THEN THE System SHALL reject the deletion with a 409 Conflict status and display a message indicating the entity is in use
9. IF an invalid entity type is requested, THEN THE System SHALL return a 404 Not Found response indicating the entity type is not recognized

### Requirement 10: Email Notification History

**User Story:** As an Operations user, I want to view the email communication history for a booking, so that I can verify which notifications were sent and their delivery status.

#### Acceptance Criteria

1. THE Notification_View SHALL display within the booking detail page as a section showing communication logs
2. THE Notification_View SHALL fetch communication logs from the booking detail response (communication_logs related field)
3. THE Notification_View SHALL display email_type, recipients, sent_at, and status for each log entry
4. IF a communication log has a status of "failed", THEN THE Notification_View SHALL display the error_message in a visually distinct warning style (red background or red text)
5. THE Notification_View SHALL sort entries by created_at descending (most recent first)
6. IF no communication logs exist for the booking, THEN THE Notification_View SHALL display a message indicating no notifications have been sent yet
7. IF the sent_at field is null, THEN THE Notification_View SHALL display "Pending" in place of the timestamp

### Requirement 11: Responsive Layout and Navigation

**User Story:** As a user, I want the application to be usable on both desktop and tablet devices, so that I can work from different form factors.

#### Acceptance Criteria

1. THE Frontend_App SHALL provide a persistent sidebar navigation on desktop viewports (≥1024px) displaying links to Dashboard and Bookings for all authenticated roles, Reports for Admin, Operations, and Accounts roles, and Master Data for Admin role only
2. WHILE the viewport width is less than 1024px, THE Frontend_App SHALL collapse the sidebar into a hamburger menu button that toggles the navigation panel open and closed on tap, and SHALL close the navigation panel when the user selects a link
3. THE Frontend_App SHALL display the logged-in user's full name and role label (as returned by the authentication API) in the navigation header
4. WHEN an API request has been pending for longer than 300ms, THE Frontend_App SHALL display a non-blocking loading indicator, and SHALL remove the indicator within 100ms of the response being received or the request failing
5. THE Frontend_App SHALL visually distinguish the currently active navigation link corresponding to the current route from inactive links

### Requirement 12: Deployment Configuration

**User Story:** As a DevOps engineer, I want the React build to be served via the existing Nginx reverse proxy, so that the frontend and API share a single domain.

#### Acceptance Criteria

1. THE Frontend_App SHALL produce a static production build output to a /build directory containing index.html, CSS bundle(s), and JS bundle(s) with content-hashed filenames for cache busting
2. THE Frontend_App SHALL use relative API paths (/api/) so that requests are proxied to the Django backend by Nginx on the same domain
3. THE Frontend_App SHALL include a multi-stage Dockerfile that installs dependencies, builds the React app, and copies the /build output to /usr/share/nginx/html in a final nginx:alpine stage
4. THE Nginx configuration SHALL route requests to /api/ and /admin/ to the Django upstream, serve /static/ from the Django staticfiles volume, and serve all other paths from the React build directory with a try_files $uri $uri/ /index.html fallback to support SPA client-side routing
