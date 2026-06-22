# Implementation Tasks

## Task 1: Create Proforma Invoice Django App and Models

### Description
Set up the `proforma` Django app with the ProformaInvoice and ProformaLineItem models, including migrations and admin registration.

### Steps
- [x] 1.1 Create the `proforma` Django app: `python manage.py startapp proforma`
- [x] 1.2 Add `proforma` to INSTALLED_APPS in `logistics/settings.py`
- [x] 1.3 Create `ProformaInvoice` model with fields: pi_number (CharField, unique, auto-generated), date (DateField), customer (FK to Client), currency (CharField with USD/INR choices), exchange_rate (DecimalField), payment_terms (TextField), expected_shipment_date (DateField), total_amount (DecimalField), status (CharField with DRAFT/SENT/APPROVED/PAYMENT_PENDING/PAID choices), created_by (FK to User), created_at, updated_at
- [x] 1.4 Create `ProformaLineItem` model with fields: proforma_invoice (FK to ProformaInvoice, CASCADE), product_name (CharField), quantity (DecimalField), rate (DecimalField), amount (DecimalField)
- [x] 1.5 Implement `generate_pi_number()` function using format `PI-YYYYMM-NNNN` with sequential numbering per month
- [x] 1.6 Override `ProformaInvoice.save()` to auto-generate pi_number on creation and compute total_amount from line items
- [x] 1.7 Register models in `proforma/admin.py` with inline ProformaLineItem admin
- [x] 1.8 Create and run migrations: `python manage.py makemigrations proforma && python manage.py migrate`

## Task 2: Proforma Invoice API (Serializers, Views, URLs)

### Description
Implement DRF serializers, viewset, and URL routing for Proforma Invoice CRUD and status transitions.

### Steps
- [x] 2.1 Create `proforma/serializers.py` with `ProformaInvoiceCreateSerializer` (validates line items, customer FK, currency, dates), `ProformaLineItemSerializer`, and `ProformaInvoiceDetailSerializer` (read-only, includes line items and payment summary)
- [x] 2.2 Create `proforma/services.py` with `ProformaService` class containing methods: `create_proforma(data, user)`, `update_proforma(pi_id, data, user)`, `change_status(pi_id, new_status, user)` — validates status transitions against allowed map
- [x] 2.3 Create `proforma/views.py` with `ProformaInvoiceViewSet` using permission classes: Accounts/Admin for write, Sales (filtered) for read
- [x] 2.4 Implement Sales_User queryset filtering: only PIs where customer is linked to Sales_User's marketing_person assignments
- [x] 2.5 Add `@action(detail=True, methods=['patch'], url_path='status')` for status transitions with validation
- [x] 2.6 Create `proforma/urls.py` with router registration and include in main `logistics/urls.py` at path `api/proforma-invoices/`
- [x] 2.7 Add validation that at least one line item exists before saving
- [x] 2.8 Add validation that line_item.amount == quantity * rate for each line item

## Task 3: Payment Django App and Models

### Description
Set up the `payments` Django app with the Payment model.

### Steps
- [x] 3.1 Create the `payments` Django app: `python manage.py startapp payments`
- [x] 3.2 Add `payments` to INSTALLED_APPS in `logistics/settings.py`
- [x] 3.3 Create `Payment` model with fields: proforma_invoice (FK to ProformaInvoice, PROTECT), amount (DecimalField), payment_mode (CharField with BANK/CASH/LC choices), payment_date (DateField), reference_number (CharField, optional), notes (TextField, optional), created_by (FK to User), created_at
- [x] 3.4 Create and run migrations

## Task 4: Payment API (Serializers, Views, URLs)

### Description
Implement DRF serializers, views, and URL routing for Payment CRUD with business logic validation.

### Steps
- [x] 4.1 Create `payments/serializers.py` with `PaymentCreateSerializer` (validates amount does not exceed remaining balance) and `PaymentDetailSerializer` (includes customer name, PI total, outstanding balance)
- [x] 4.2 Create `payments/services.py` with `PaymentService` class: `record_payment(data, user)` — validates amount, creates payment, auto-transitions PI status (to PAYMENT_PENDING on first payment, to PAID when fully paid)
- [x] 4.3 Create `payments/views.py` with `PaymentViewSet` using permission classes: Accounts/Admin for write and read
- [x] 4.4 Create `payments/urls.py` and include in main urls at path `api/payments/`
- [x] 4.5 Add nested route on ProformaInvoice: GET `/api/proforma-invoices/{id}/payments/` listing payments for that PI
- [x] 4.6 Implement outstanding balance computation: `pi.total_amount - sum(payments.amount)`

## Task 5: Inventory Django App and Models

### Description
Set up the `inventory` Django app with the StockItem model.

### Steps
- [x] 5.1 Create the `inventory` Django app: `python manage.py startapp inventory`
- [x] 5.2 Add `inventory` to INSTALLED_APPS in `logistics/settings.py`
- [x] 5.3 Create `StockItem` model with fields: product_name (CharField, unique), available_stock (PositiveIntegerField, default=0), reserved_stock (PositiveIntegerField, default=0), shipped_stock (PositiveIntegerField, default=0), unit (CharField, default='units'), updated_at
- [x] 5.4 Add database constraint: available_stock >= 0, reserved_stock >= 0, shipped_stock >= 0
- [x] 5.5 Register model in admin and create migrations

## Task 6: Inventory API and Stuffing Action

### Description
Implement stock item CRUD and the critical container stuffing action that triggers stock deduction.

### Steps
- [x] 6.1 Create `inventory/serializers.py` with `StockItemSerializer` (CRUD) and `StuffingActionSerializer` (validates product_quantities list)
- [x] 6.2 Create `inventory/services.py` with `StockService` class: `perform_stuffing(container_id, product_quantities, user)` — atomic operation using `select_for_update()`, validates sufficient stock, deducts available, increments shipped
- [x] 6.3 Ensure stuffing is all-or-nothing: if any product has insufficient stock, raise ValidationError without modifying any records
- [x] 6.4 Create `inventory/views.py` with `StockItemViewSet` (Operations/Admin) and stuffing action endpoint
- [x] 6.5 Create stuffing endpoint: POST `/api/bookings/{id}/containers/{cid}/stuff/` — calls StockService.perform_stuffing, updates container.stuffing_status to STUFFED, records stuffed_at and stuffed_by
- [x] 6.6 Create `inventory/urls.py` and include in main urls at path `api/stock-items/`
- [x] 6.7 Add the stuffing endpoint to bookings urls

## Task 7: Modify Existing Booking Model

### Description
Extend the Booking and Container models with new fields for the freight workflow.

### Steps
- [x] 7.1 Add extended status choices to Booking.Status: PENDING, BOOKED, STUFFING, SHIPPED, COMPLETED (replace existing DO_BOOKING_EDIT and COMPLETED with new set)
- [x] 7.2 Add `proforma_invoice` FK (nullable, SET_NULL) to Booking model pointing to `proforma.ProformaInvoice`
- [x] 7.3 Add `stuffing_status` field to Container model with choices PENDING/STUFFED, default PENDING
- [x] 7.4 Add `stuffed_at` (DateTimeField, nullable) and `stuffed_by` (FK to User, nullable) to Container model
- [x] 7.5 Update `BookingService.change_status()` to validate new transition map: PENDING → BOOKED → STUFFING → SHIPPED → COMPLETED
- [x] 7.6 Add validation in status transition to SHIPPED: all containers must have stuffing_status == STUFFED
- [x] 7.7 Create and run migrations for bookings app changes
- [x] 7.8 Update `BookingCreateSerializer` and `BookingUpdateSerializer` to accept optional `proforma_invoice` field
- [x] 7.9 Update `BookingDetailSerializer` to include proforma_invoice reference and container stuffing_status

## Task 8: Commercial Invoice and Packing List Models

### Description
Create the `invoices` Django app with CommercialInvoice, CommercialInvoiceLineItem, PackingList, and PackingListLineItem models.

### Steps
- [x] 8.1 Create the `invoices` Django app: `python manage.py startapp invoices`
- [x] 8.2 Add `invoices` to INSTALLED_APPS in `logistics/settings.py`
- [x] 8.3 Create `CommercialInvoice` model with fields: booking (FK, PROTECT), invoice_number (CharField, unique, auto-generated), revision (PositiveIntegerField, default=1), status (DRAFT/FINALIZED), created_by, created_at, updated_at
- [x] 8.4 Create `CommercialInvoiceLineItem` model with fields: commercial_invoice (FK, CASCADE), product_name, quantity, rate, amount, net_weight, gross_weight, hs_code, num_packages
- [x] 8.5 Create `PackingList` model with fields: booking (FK, PROTECT), packing_list_number (CharField, unique, auto-generated), revision, status, created_by, created_at, updated_at
- [x] 8.6 Create `PackingListLineItem` model with fields: packing_list (FK, CASCADE), product_name, quantity, num_packages, net_weight, gross_weight, package_type
- [x] 8.7 Create and run migrations

## Task 9: Commercial Invoice and Packing List API

### Description
Implement API endpoints for Commercial Invoice and Packing List with auto-fill from PI data and document versioning.

### Steps
- [x] 9.1 Create `invoices/serializers.py` with serializers for CommercialInvoice, CommercialInvoiceLineItem, PackingList, PackingListLineItem (create and detail variants)
- [x] 9.2 Create `invoices/services.py` with: `create_commercial_invoice(booking_id, user)` — auto-fills line items from linked PI, `finalize_invoice(invoice_id, user)` — validates and locks, `create_revision(invoice_id, user)` — creates new revision from finalized
- [x] 9.3 Add same service methods for PackingList: `create_packing_list`, `finalize_packing_list`, `create_packing_list_revision`
- [x] 9.4 Create `invoices/views.py` with views for both models, including finalize action and auto-fill endpoint
- [x] 9.5 Create `invoices/urls.py` and register in main urls at paths: `/api/bookings/{id}/commercial-invoice/`, `/api/bookings/{id}/packing-list/`, `/api/commercial-invoices/{id}/`, `/api/packing-lists/{id}/`
- [x] 9.6 Implement document versioning: when modifying a finalized document, create a new record with revision = previous_revision + 1
- [x] 9.7 Prevent edits to finalized documents (return 400 error with message)

## Task 10: Bill of Lading Django App and API

### Description
Create the `bl` Django app with the BillOfLading model and full API including auto-fill and status management.

### Steps
- [x] 10.1 Create the `bl` Django app: `python manage.py startapp bl`
- [x] 10.2 Add `bl` to INSTALLED_APPS in `logistics/settings.py`
- [x] 10.3 Create `BillOfLading` model with fields: booking (FK, PROTECT), bl_number (CharField, unique), bl_type (LINE/DIRECT choices), status (DRAFT/SUBMITTED/RELEASED), container_number, vessel_name, voyage_number, shipper (FK), consignee (FK), notify_party (TextField), cargo_description (TextField), created_by, created_at, updated_at
- [x] 10.4 Create `bl/serializers.py` with `BLCreateSerializer` (validates required fields, bl_type) and `BLDetailSerializer`
- [x] 10.5 Create `bl/services.py` with: `create_bl(booking_id, data, user)` — auto-fills from Booking/Invoice data if available, `change_bl_status(bl_id, new_status, user)` — validates transition DRAFT→SUBMITTED→RELEASED
- [x] 10.6 Create `bl/views.py` with BL ViewSet, status change action, Operations/Admin permissions
- [x] 10.7 Create `bl/urls.py` and register: `/api/bookings/{id}/bl/`, `/api/bl/{id}/`, `/api/bl/{id}/status/`
- [x] 10.8 Implement auto-fill logic: populate vessel_name, voyage_number from Booking; container_number from Booking containers; shipper/consignee from Booking FKs; cargo_description from Commercial Invoice line items
- [x] 10.9 Create and run migrations

## Task 11: Dashboard API Endpoints

### Description
Implement backend API endpoints for the enhanced dashboard with KPI cards and workflow sections.

### Steps
- [x] 11.1 Create `dashboard/` directory in the existing project structure (or add to an existing appropriate app like `reports`)
- [x] 11.2 Implement GET `/api/dashboard/kpis/` — returns: total_pis (count), pending_payments (PI count in PAYMENT_PENDING), active_shipments (Bookings not COMPLETED), containers_in_transit (containers on active bookings), stock_available (sum of available_stock)
- [x] 11.3 Implement GET `/api/dashboard/proforma-status/` — returns paginated list of non-Paid PIs with pi_number, customer_name, amount, status
- [x] 11.4 Implement GET `/api/dashboard/ready-for-booking/` — returns PIs with status PAID and no linked Bookings
- [x] 11.5 Implement GET `/api/dashboard/current-shipments/` — returns active Bookings with job_number, customer, container info, status, etd, eta
- [x] 11.6 Implement GET `/api/dashboard/document-status/` — returns counts: invoice_pending, packing_list_pending, bl_pending
- [x] 11.7 Implement GET `/api/dashboard/alerts/` — returns: payment_overdue (PIs in PAYMENT_PENDING > 30 days), shipment_delay (ETD passed, not shipped), missing_bl (shipped bookings without BL)
- [x] 11.8 Create URL routing and register in main urls at path `api/dashboard/`

## Task 12: Operations Tracking View API

### Description
Implement the Operations View API endpoint with filtering, sorting, and pagination.

### Steps
- [x] 12.1 Create operations view endpoint: GET `/api/operations/` with permission for Operations/Admin users
- [x] 12.2 Return fields: pi_number, booking_number (job_number), consignee, shipping_line, container_type, vessel_name, voyage, pol, pod, fpd, etd, eta, forwarder
- [x] 12.3 Implement filtering via django-filters: customer, shipping_line, status, etd_date_range (etd_from, etd_to), pol
- [x] 12.4 Implement ordering via OrderingFilter on all displayed columns
- [x] 12.5 Use existing StandardPagination (page_size=25)
- [x] 12.6 Add URL to main urls.py

## Task 13: Smart Automations Backend

### Description
Implement backend automation logic for auto-create booking, auto-fill documents, and alert generation.

### Steps
- [ ] 13.1 In `proforma/services.py`, add `auto_create_booking(pi_id, user)` — creates Booking pre-filled with customer and expected_shipment_date from PI, links PI to Booking
- [ ] 13.2 Add a Celery task `check_payment_overdue` that runs daily, identifies PIs in PAYMENT_PENDING for >30 days, and sends reminder email via SES
- [ ] 13.3 Add a Celery task `check_pending_bl` that runs daily, identifies Bookings with status SHIPPED and no BL or BL in DRAFT for >7 days after ETD, and creates alert records
- [ ] 13.4 Create an `Alert` model (or use the existing notification infrastructure) to store alert records with type, message, related_object, is_read, created_at
- [ ] 13.5 Implement alert dismissal endpoint: PATCH `/api/alerts/{id}/dismiss/`
- [ ] 13.6 Register Celery tasks in app config and add beat schedule for daily execution

## Task 14: Enhanced Email Notifications

### Description
Extend existing email notification service with PI data in booking confirmation and BL data in onboard confirmation.

### Steps
- [ ] 14.1 Update `notifications/services.py` `send_booking_confirmation()` to include PI Number, Customer Name, and Total Amount when the Booking has a linked Proforma Invoice
- [ ] 14.2 Update the booking confirmation HTML template to display PI information section
- [ ] 14.3 Update `send_onboard_confirmation()` to include BL Number from the Booking's linked BillOfLading
- [ ] 14.4 Update the onboard confirmation HTML template to display BL number in the container table
- [ ] 14.5 Create `send_payment_reminder(pi_id)` method that sends overdue payment reminder to customer email
- [ ] 14.6 Create payment reminder HTML email template

## Task 15: Permissions for New Features

### Description
Add permission classes for the new feature endpoints following existing patterns.

### Steps
- [ ] 15.1 Add `CanManageProforma` permission class: allows Accounts and Admin users write access
- [ ] 15.2 Add `CanViewProforma` permission class: allows Accounts, Admin, and Sales users read access (Sales with queryset filtering)
- [ ] 15.3 Add `CanManagePayments` permission class: allows Accounts and Admin users
- [ ] 15.4 Add `CanManageInventory` permission class: allows Operations and Admin users
- [ ] 15.5 Add `CanPerformStuffing` permission class: allows Operations and Admin users
- [ ] 15.6 Add `CanManageDocuments` permission class: allows Accounts, Operations, and Admin users (for Commercial Invoice, Packing List)
- [ ] 15.7 Add `CanManageBL` permission class: allows Operations and Admin users
- [ ] 15.8 Apply permissions to all new viewsets and views

## Task 16: Frontend - Proforma Invoice Pages

### Description
Build React frontend pages for Proforma Invoice management.

### Steps
- [ ] 16.1 Create `frontend/src/features/proforma/` directory with page and component files
- [ ] 16.2 Create `ProformaListPage.tsx` with table listing PIs (PI Number, Customer, Amount, Currency, Status, Date), pagination, and status filter
- [ ] 16.3 Create `ProformaFormPage.tsx` with form for creating/editing PIs: customer dropdown, currency selector, date pickers, payment terms textarea, expected shipment date, and dynamic line item table (add/remove rows)
- [ ] 16.4 Create `ProformaDetailPage.tsx` showing full PI details, linked bookings, payment history, and status actions (Send, Approve, etc.)
- [ ] 16.5 Create `PIStatusBadge.tsx` component with color-coded status badges
- [ ] 16.6 Create `LineItemTable.tsx` component for editable product line items with auto-calculated amount (qty × rate) and total
- [ ] 16.7 Add API hooks using TanStack Query: `useProformaList`, `useProformaDetail`, `useCreateProforma`, `useUpdateProforma`, `useChangeProformaStatus`
- [ ] 16.8 Add routes to React Router: `/proforma`, `/proforma/new`, `/proforma/:id`
- [ ] 16.9 Add "Proforma Invoices" to Sidebar navigation with role-based visibility (Accounts, Admin, Sales)

## Task 17: Frontend - Payment Pages

### Description
Build React frontend pages for Payment management.

### Steps
- [ ] 17.1 Create `frontend/src/features/payments/` directory
- [ ] 17.2 Create `PaymentListPage.tsx` with table listing payments (PI Number, Customer, Amount, Mode, Date, Status)
- [ ] 17.3 Create `PaymentFormPage.tsx` with form: PI selector (searchable dropdown), amount input, payment mode selector, date picker, reference number, notes
- [ ] 17.4 Display read-only computed fields: Customer Name, PI Total Amount, Outstanding Balance
- [ ] 17.5 Add validation: prevent submit if amount > outstanding balance
- [ ] 17.6 Add API hooks: `usePaymentList`, `useCreatePayment`, `useProformaPayments`
- [ ] 17.7 Add routes: `/payments`, `/payments/new`
- [ ] 17.8 Add "Payments" to Sidebar navigation (Accounts, Admin only)

## Task 18: Frontend - Inventory Pages

### Description
Build React frontend pages for Stock/Inventory management.

### Steps
- [ ] 18.1 Create `frontend/src/features/inventory/` directory
- [ ] 18.2 Create `StockListPage.tsx` with table showing: Product Name, Available Stock, Reserved Stock, Shipped Stock, Unit
- [ ] 18.3 Create `StockFormPage.tsx` for creating/editing stock items
- [ ] 18.4 Create `StockLevelIndicator.tsx` component showing visual bar for stock levels (green/yellow/red based on available quantity)
- [ ] 18.5 Add API hooks: `useStockList`, `useCreateStockItem`, `useUpdateStockItem`
- [ ] 18.6 Add routes: `/inventory`, `/inventory/new`, `/inventory/:id/edit`
- [ ] 18.7 Add "Inventory" to Sidebar navigation (Operations, Admin only)

## Task 19: Frontend - Commercial Invoice and Packing List Pages

### Description
Build React frontend pages for Commercial Invoice and Packing List management with auto-fill functionality.

### Steps
- [ ] 19.1 Create `frontend/src/features/invoices/` directory
- [ ] 19.2 Create `CommercialInvoicePage.tsx` — form/view for commercial invoice with editable line items (product, qty, rate, amount, net weight, gross weight, HS code, packages), auto-filled from PI on creation
- [ ] 19.3 Create `PackingListPage.tsx` — form/view for packing list with line items (product, qty, packages, net weight, gross weight, package type), auto-filled from PI
- [ ] 19.4 Create `DocumentVersionHistory.tsx` component showing revision history with revision number, date, and user
- [ ] 19.5 Implement "Finalize" action button that locks the document and shows confirmation dialog
- [ ] 19.6 Implement "Create Revision" button on finalized documents that creates editable copy
- [ ] 19.7 Add API hooks: `useCommercialInvoice`, `useCreateInvoice`, `useFinalizeInvoice`, `usePackingList`, `useCreatePackingList`, `useFinalizePackingList`
- [ ] 19.8 Access these pages from Booking detail page (linked from booking → documents section)

## Task 20: Frontend - Bill of Lading Pages

### Description
Build React frontend pages for Bill of Lading management.

### Steps
- [ ] 20.1 Create `frontend/src/features/bl/` directory
- [ ] 20.2 Create `BLFormPage.tsx` with form: BL Number, BL Type (Line/Direct), Container Number, Vessel Name, Voyage Number, Shipper (dropdown), Consignee (dropdown), Notify Party (textarea), Cargo Description (textarea) — auto-filled where data is available
- [ ] 20.3 Create `BLDetailPage.tsx` showing full BL details with status actions (Submit, Release)
- [ ] 20.4 Create `BLStatusBadge.tsx` component with color-coded badges
- [ ] 20.5 Show auto-fill preview when creating BL for a booking with existing Commercial Invoice
- [ ] 20.6 Add API hooks: `useBLForBooking`, `useCreateBL`, `useUpdateBL`, `useChangeBLStatus`
- [ ] 20.7 Access BL pages from Booking detail page (documents section)
- [ ] 20.8 Add alert banner on Booking detail when BL is missing or pending

## Task 21: Frontend - Enhanced Dashboard

### Description
Build the enhanced dashboard page with KPI cards and workflow sections.

### Steps
- [ ] 21.1 Create `frontend/src/features/dashboard/` directory with DashboardPage and components
- [ ] 21.2 Create `KPICard.tsx` component (reusable card with title, value, icon, optional trend indicator)
- [ ] 21.3 Create `DashboardPage.tsx` with layout: KPI cards row at top, then tabbed/sectioned workflow areas below
- [ ] 21.4 Implement KPI cards section: Total PIs, Pending Payments, Active Shipments, Containers in Transit, Stock Available
- [ ] 21.5 Create `ProformaStatusSection.tsx` — table of non-Paid PIs with status badges
- [ ] 21.6 Create `ReadyForBookingSection.tsx` — table of Paid PIs without bookings, with "Create Booking" action button
- [ ] 21.7 Create `CurrentShipmentsSection.tsx` — table of active bookings with container/shipment info
- [ ] 21.8 Create `DocumentStatusSection.tsx` — counts of pending invoices, packing lists, BLs with links
- [ ] 21.9 Create `AlertsSection.tsx` — list of alerts (overdue payments, shipment delays, missing BLs) with dismiss action
- [ ] 21.10 Add API hooks: `useDashboardKPIs`, `useProformaStatus`, `useReadyForBooking`, `useCurrentShipments`, `useDocumentStatus`, `useAlerts`
- [ ] 21.11 Set Dashboard as the landing page after login, add to Sidebar as first item

## Task 22: Frontend - Operations Tracking View

### Description
Build the Operations tracking page with table, filters, and sorting.

### Steps
- [ ] 22.1 Create `frontend/src/features/operations/` directory
- [ ] 22.2 Create `OperationsPage.tsx` with full-width table showing: PI No, Booking No, Consignee, Shipping Line, Container Type, Vessel, Voyage, POL, POD, FPD, ETD, ETA, Forwarder
- [ ] 22.3 Create filter bar with: Customer dropdown, Shipping Line dropdown, Status dropdown, ETD date range picker, POL dropdown
- [ ] 22.4 Implement column sorting (clickable headers)
- [ ] 22.5 Add pagination controls with configurable page size
- [ ] 22.6 Add API hook: `useOperationsView` with filter/sort/pagination params
- [ ] 22.7 Add routes: `/operations`
- [ ] 22.8 Add "Operations" to Sidebar navigation (Operations, Admin only)

## Task 23: Frontend - Container Stuffing UI

### Description
Build the container stuffing action interface within the booking detail page.

### Steps
- [ ] 23.1 Add "Stuffing" section to Booking detail page showing containers with their stuffing status
- [ ] 23.2 Create stuffing action dialog/modal: shows products from linked PI, allows entering quantities per product for the container
- [ ] 23.3 Add validation: quantity per product must not exceed available stock (show available stock in the form)
- [ ] 23.4 Add "Mark as Stuffed" button per container (disabled if already stuffed)
- [ ] 23.5 Show confirmation dialog before performing stuffing action (irreversible stock impact)
- [ ] 23.6 Add API hook: `usePerformStuffing` that calls POST `/api/bookings/{id}/containers/{cid}/stuff/`
- [ ] 23.7 Update container list display to show stuffing status badge and stuffed_at timestamp

## Task 24: Frontend - Role-Based Navigation and Guards

### Description
Update frontend routing and navigation to enforce role-based access for all new features.

### Steps
- [ ] 24.1 Update `RoleGuard.tsx` to support the new feature routes with appropriate role checks
- [ ] 24.2 Update `Sidebar.tsx` to conditionally show new navigation items based on user role: Dashboard (all), Proforma (Accounts, Admin, Sales), Payments (Accounts, Admin), Inventory (Operations, Admin), Operations View (Operations, Admin), BL (Operations, Admin)
- [ ] 24.3 Add route definitions for all new pages in the router configuration
- [ ] 24.4 Ensure Sales_Users see filtered data on Proforma list (handled by backend, but show "My Proformas" label)
- [ ] 24.5 Add proper error boundary handling for 403 responses — show "Access Denied" page

## Task 25: Backend Tests

### Description
Write comprehensive tests for all new backend functionality.

### Steps
- [ ] 25.1 Write tests for ProformaInvoice CRUD and PI number generation (test uniqueness, format, sequential behavior)
- [ ] 25.2 Write tests for PI status transitions (valid and invalid transitions)
- [ ] 25.3 Write tests for Payment creation with validation (exceed balance, negative amounts, valid creation)
- [ ] 25.4 Write tests for Payment status auto-computation (partial paid, fully paid)
- [ ] 25.5 Write tests for StockItem CRUD and constraints (non-negative values)
- [ ] 25.6 Write tests for stuffing action: successful deduction, insufficient stock rejection, atomicity (no partial deductions), duplicate stuffing rejection
- [ ] 25.7 Write tests for Commercial Invoice creation with auto-fill from PI, finalization, versioning
- [ ] 25.8 Write tests for Packing List creation, finalization, versioning
- [ ] 25.9 Write tests for BL creation with auto-fill, status transitions, validation
- [ ] 25.10 Write tests for Booking status extension (new transitions, stuffing prerequisite for SHIPPED)
- [ ] 25.11 Write tests for Dashboard KPI computation
- [ ] 25.12 Write tests for role-based access control on all new endpoints
- [ ] 25.13 Write tests for partial shipment allocation (allocation does not exceed PI line item quantity)
- [ ] 25.14 Write tests for auto-create booking from paid PI
