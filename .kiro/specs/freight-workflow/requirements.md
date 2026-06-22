# Requirements Document

## Introduction

This document specifies the requirements for a full freight forwarding workflow expansion to the existing logistics ERP platform. The expansion introduces Proforma Invoice management, payment tracking, stock/inventory control, commercial invoice and packing list generation, Bill of Lading management, an enhanced dashboard, smart automations, and an operations tracking view. These capabilities connect the entire order-to-shipment lifecycle: PI → Payment → Booking → Stuffing → Invoice → BL.

## Glossary

- **Platform**: The logistics ERP web application comprising a React frontend and Django REST API backend
- **Proforma_Invoice**: A preliminary invoice issued to a customer before shipment, detailing products, quantities, rates, and payment terms
- **PI_Line_Item**: An individual product row within a Proforma Invoice containing product name, quantity, rate, and computed amount
- **Payment**: A financial transaction recording money received from a customer against a Proforma Invoice
- **Stock_Item**: An inventory record tracking available, reserved, and shipped quantities of a product
- **Commercial_Invoice**: A formal trade invoice generated after container stuffing, containing final shipment details including weights and HS codes
- **Packing_List**: A document detailing the physical packaging of goods within a shipment, including package counts, weights, and dimensions
- **Bill_of_Lading**: A legal shipping document issued by a carrier acknowledging receipt of cargo for shipment
- **Dashboard**: The main overview page displaying KPI cards, workflow status sections, and alert notifications
- **Stuffing_Action**: The operational event of loading goods into a container, which triggers stock deduction
- **Operations_View**: A tabular tracking interface showing the consolidated status of all active shipments
- **Automation_Engine**: The backend service responsible for triggering automatic actions based on workflow state changes
- **Admin_User**: A user assigned to the Admin group with full system access
- **Operations_User**: A user assigned to the Operations group managing bookings, containers, stuffing, documents, and shipments
- **Accounts_User**: A user assigned to the Accounts group managing proforma invoices, payments, invoices, and reports
- **Sales_User**: A user assigned to the Sales group with read-only access to proforma invoices and shipments filtered to their assigned clients
- **Exchange_Rate**: A conversion factor between USD and INR currencies applied at the time of Proforma Invoice creation

## Requirements

### Requirement 1: Proforma Invoice Creation

**User Story:** As an Accounts_User, I want to create a Proforma Invoice with product line items and payment terms, so that I can issue a formal price quotation to a customer before shipment.

#### Acceptance Criteria

1. WHEN an Accounts_User or Admin_User submits a new Proforma Invoice, THE Platform SHALL auto-generate a unique PI Number in the format "PI-YYYYMM-NNNN" where NNNN is a zero-padded sequential number
2. THE Platform SHALL require the following fields for Proforma Invoice creation: PI Date, Customer (reference to Client master data), Currency (USD or INR), Payment Terms, and Expected Shipment Date
3. WHEN a Proforma Invoice is created, THE Platform SHALL accept one or more PI_Line_Items each containing: Product Name, Quantity (positive decimal), Rate (positive decimal), and computed Amount (Quantity multiplied by Rate)
4. THE Platform SHALL compute the Total Amount as the sum of all PI_Line_Item amounts and store it on the Proforma Invoice
5. WHEN a Proforma Invoice is saved without sending, THE Platform SHALL assign the status "Draft"
6. THE Platform SHALL validate that at least one PI_Line_Item exists before allowing a Proforma Invoice to be saved

### Requirement 2: Proforma Invoice Status Lifecycle

**User Story:** As an Accounts_User, I want to advance a Proforma Invoice through defined statuses, so that I can track its progress from creation to payment completion.

#### Acceptance Criteria

1. THE Platform SHALL enforce the following Proforma Invoice status transitions: Draft → Sent → Approved → Payment_Pending → Paid
2. WHEN an Accounts_User triggers "Send to Customer," THE Platform SHALL transition the Proforma Invoice status from Draft to Sent
3. WHEN an Accounts_User marks a Proforma Invoice as Approved, THE Platform SHALL transition the status from Sent to Approved
4. WHEN the first Payment is recorded against an Approved Proforma Invoice, THE Platform SHALL transition the status to Payment_Pending
5. WHEN total payments received equal or exceed the Total Amount, THE Platform SHALL transition the Proforma Invoice status to Paid
6. IF a user attempts a status transition that violates the defined sequence, THEN THE Platform SHALL reject the transition and return a descriptive error message

### Requirement 3: Proforma Invoice Multi-Currency Support

**User Story:** As an Accounts_User, I want to create Proforma Invoices in USD or INR, so that I can serve customers who transact in different currencies.

#### Acceptance Criteria

1. THE Platform SHALL support two currencies for Proforma Invoices: USD and INR
2. WHEN a Proforma Invoice is created, THE Platform SHALL require a currency selection of either USD or INR
3. THE Platform SHALL store an Exchange_Rate on each Proforma Invoice representing the USD-to-INR conversion factor at the time of creation
4. THE Platform SHALL display all monetary amounts on a Proforma Invoice in the selected currency

### Requirement 4: Proforma Invoice to Booking Linkage

**User Story:** As an Operations_User, I want to link Proforma Invoices to Bookings, so that I can trace the full lifecycle from quotation to shipment.

#### Acceptance Criteria

1. THE Platform SHALL support linking one Proforma Invoice to one or more Bookings to enable partial shipments
2. THE Platform SHALL support linking one Booking to exactly one Proforma Invoice
3. WHEN a Booking is linked to a Proforma Invoice, THE Platform SHALL store the association as a foreign key on the Booking record
4. THE Platform SHALL provide a navigable chain from Proforma Invoice → Booking → Commercial Invoice → Bill of Lading
5. WHEN a user views a Proforma Invoice detail, THE Platform SHALL display all linked Bookings with their current statuses

### Requirement 5: Payment Recording

**User Story:** As an Accounts_User, I want to record payments against a Proforma Invoice, so that I can track how much a customer has paid.

#### Acceptance Criteria

1. WHEN an Accounts_User creates a Payment, THE Platform SHALL require: linked Proforma Invoice, Payment Amount (positive decimal), Payment Mode (Bank, Cash, or LC), and Payment Date
2. THE Platform SHALL display the Customer name and Total PI Amount as read-only fields derived from the linked Proforma Invoice
3. THE Platform SHALL compute and display the outstanding balance as Total PI Amount minus the sum of all payments recorded against that Proforma Invoice
4. IF a Payment Amount would cause total payments to exceed the Total PI Amount, THEN THE Platform SHALL reject the payment and return an error message
5. THE Platform SHALL record each payment as an individual transaction, supporting multiple partial payments against a single Proforma Invoice

### Requirement 6: Payment Status Logic

**User Story:** As an Accounts_User, I want the system to automatically determine payment status, so that I can identify which invoices are partially or fully paid.

#### Acceptance Criteria

1. WHEN total payments recorded are greater than zero but less than the Total PI Amount, THE Platform SHALL display the payment status as "Partial_Paid"
2. WHEN total payments recorded equal or exceed the Total PI Amount, THE Platform SHALL display the payment status as "Fully_Paid"
3. WHEN the Proforma Invoice status transitions to Paid, THE Platform SHALL mark the Proforma Invoice as "Ready for Booking"
4. THE Platform SHALL display a "Ready for Booking" indicator on Proforma Invoices that are fully paid and have no linked Booking

### Requirement 7: Auto-Create Booking from Payment

**User Story:** As an Operations_User, I want the option to automatically create a booking when payment is received, so that I can expedite the shipment workflow.

#### Acceptance Criteria

1. WHEN a Proforma Invoice reaches "Paid" status, THE Platform SHALL present an option to auto-create a Booking
2. WHERE the auto-create booking option is enabled, THE Platform SHALL create a new Booking record pre-filled with the Customer and Expected Shipment Date from the Proforma Invoice
3. WHEN a Booking is auto-created, THE Platform SHALL link the new Booking to the originating Proforma Invoice
4. THE Platform SHALL allow Operations_Users to decline auto-creation and manually create or link a Booking later

### Requirement 8: Stock Item Management

**User Story:** As an Operations_User, I want to manage product stock with available, reserved, and shipped quantities, so that I can track inventory throughout the shipment lifecycle.

#### Acceptance Criteria

1. THE Platform SHALL maintain a Stock_Item record for each product with fields: Product Name, Available Stock (non-negative integer), Reserved Stock (non-negative integer), and Shipped Stock (non-negative integer)
2. THE Platform SHALL enforce that Available Stock, Reserved Stock, and Shipped Stock are each non-negative values
3. WHEN a new Stock_Item is created, THE Platform SHALL initialize Reserved Stock and Shipped Stock to zero
4. THE Platform SHALL provide CRUD operations for Stock_Item records accessible to Operations_Users and Admin_Users

### Requirement 9: Stock Deduction on Stuffing

**User Story:** As an Operations_User, I want stock to reduce only when a container is stuffed, so that inventory remains accurate until goods physically leave the warehouse.

#### Acceptance Criteria

1. WHEN a Proforma Invoice is created, THE Platform SHALL NOT modify any Stock_Item quantities
2. WHEN a Booking is created or updated, THE Platform SHALL NOT modify any Stock_Item quantities
3. WHEN an Operations_User marks a Container as "Stuffed," THE Platform SHALL deduct the stuffed product quantities from the corresponding Stock_Item Available Stock
4. WHEN a Container is marked as "Stuffed," THE Platform SHALL add the stuffed quantities to the corresponding Stock_Item Shipped Stock
5. IF the Available Stock for any product is less than the quantity being stuffed, THEN THE Platform SHALL reject the stuffing action and return an error indicating insufficient stock
6. THE Platform SHALL record the stuffing timestamp and the user who performed the Stuffing_Action

### Requirement 10: Container Stuffing Status

**User Story:** As an Operations_User, I want to mark containers as stuffed, so that the system can track which containers have been loaded and trigger stock deductions.

#### Acceptance Criteria

1. THE Platform SHALL add a "stuffing_status" field to the Container model with values: Pending, Stuffed
2. WHEN an Operations_User performs the Stuffing_Action on a Container, THE Platform SHALL transition the container stuffing_status from Pending to Stuffed
3. WHEN a Container is marked as Stuffed, THE Platform SHALL record the stuffing date and the user who performed the action
4. IF a Container is already in "Stuffed" status, THEN THE Platform SHALL reject a duplicate stuffing action
5. THE Platform SHALL allow associating product quantities (from the linked Proforma Invoice line items) with a Container during the Stuffing_Action

### Requirement 11: Commercial Invoice Generation

**User Story:** As an Accounts_User, I want to generate a Commercial Invoice after container stuffing, so that I can produce the formal trade document required for customs clearance.

#### Acceptance Criteria

1. WHEN an Accounts_User initiates Commercial Invoice creation for a Booking, THE Platform SHALL auto-populate product details (Product Name, Quantity, Rate, Amount) from the linked Proforma Invoice
2. THE Platform SHALL provide editable fields on the Commercial Invoice: Final Quantity, Net Weight, Gross Weight, HS Code, and Number of Packages
3. WHEN a Commercial Invoice is created, THE Platform SHALL assign the status "Draft"
4. WHEN an Accounts_User finalizes a Commercial Invoice, THE Platform SHALL transition the status from Draft to Finalized
5. IF a Commercial Invoice is finalized, THEN THE Platform SHALL prevent further edits unless a new revision is created
6. THE Platform SHALL support document versioning by creating a new revision number when a finalized Commercial Invoice is modified
7. THE Platform SHALL link each Commercial Invoice to exactly one Booking

### Requirement 12: Packing List Generation

**User Story:** As an Accounts_User, I want to generate a Packing List alongside the Commercial Invoice, so that customs and logistics parties know the physical packaging details.

#### Acceptance Criteria

1. WHEN an Accounts_User initiates Packing List creation for a Booking, THE Platform SHALL auto-populate product details from the linked Proforma Invoice
2. THE Platform SHALL require the following fields on a Packing List: Number of Packages, Net Weight per item, Gross Weight per item, and Package Type
3. WHEN a Packing List is created, THE Platform SHALL assign the status "Draft"
4. WHEN an Accounts_User finalizes a Packing List, THE Platform SHALL transition the status from Draft to Finalized
5. THE Platform SHALL link each Packing List to exactly one Booking
6. THE Platform SHALL support document versioning for Packing Lists matching the Commercial Invoice versioning behavior

### Requirement 13: Bill of Lading Management

**User Story:** As an Operations_User, I want to manage Bill of Lading records with proper status tracking, so that I can ensure shipping documentation is complete before vessel departure.

#### Acceptance Criteria

1. THE Platform SHALL require the following fields for a Bill of Lading: BL Number, linked Booking, Container Number, Vessel Name, Voyage Number, Shipper, Consignee, and Notify Party
2. THE Platform SHALL support two BL types: Line BL and Direct BL
3. WHEN a Bill of Lading is created, THE Platform SHALL assign the status "Draft"
4. THE Platform SHALL enforce the following BL status transitions: Draft → Submitted → Released
5. WHEN a Bill of Lading is created for a Booking that has a finalized Commercial Invoice and Packing List, THE Platform SHALL auto-populate Vessel Name, Voyage Number, Container Number, Shipper, and Consignee from the Booking and linked documents
6. IF a user attempts a BL status transition that violates the defined sequence, THEN THE Platform SHALL reject the transition and return a descriptive error message

### Requirement 14: Bill of Lading Alerts

**User Story:** As an Operations_User, I want to receive alerts when a Bill of Lading is pending beyond a threshold, so that I can follow up on missing documentation.

#### Acceptance Criteria

1. WHEN a Booking has status "Shipped" and no linked Bill of Lading exists, THE Platform SHALL generate a "Missing BL" alert
2. WHEN a Bill of Lading remains in "Draft" status for more than 7 days after the Booking ETD, THE Platform SHALL generate a "Pending BL" alert
3. THE Platform SHALL display BL-related alerts on the Dashboard alerts section
4. WHEN a Bill of Lading transitions to "Released" status, THE Platform SHALL clear any associated pending alerts

### Requirement 15: Dashboard KPI Cards

**User Story:** As an Admin_User, I want to see key performance indicators on the dashboard, so that I can monitor overall business health at a glance.

#### Acceptance Criteria

1. THE Platform SHALL display the following KPI cards on the Dashboard: Total PIs (count of all Proforma Invoices), Pending Payments (count of PIs in Payment_Pending status), Active Shipments (count of Bookings with status not equal to Completed), Containers in Transit (count of Containers on Bookings with status between Booked and Shipped), and Stock Available (sum of Available Stock across all Stock_Items)
2. WHEN the Dashboard is loaded, THE Platform SHALL compute KPI values from current database state
3. THE Platform SHALL refresh KPI card values when the user navigates to or reloads the Dashboard

### Requirement 16: Dashboard Workflow Sections

**User Story:** As an Operations_User, I want the dashboard to show categorized workflow sections, so that I can quickly identify what actions need my attention.

#### Acceptance Criteria

1. THE Platform SHALL display a "Proforma Status" section showing: PI Number, Customer Name, Amount, and current Status for all non-Paid Proforma Invoices
2. THE Platform SHALL display a "Ready for Booking" section showing Proforma Invoices with status Paid that have no linked Booking, with an action button to create a Booking
3. THE Platform SHALL display a "Current Shipments" section showing: Booking Job Number, Customer Name, Container Number, Shipment Status, ETD, and ETA for all active Bookings
4. THE Platform SHALL display a "Document Status" section showing counts of: Bookings with pending Commercial Invoice, Bookings with pending Packing List, and Bookings with pending Bill of Lading
5. THE Platform SHALL display an "Alerts" section showing: overdue payments (PIs in Payment_Pending for more than 30 days), shipment delays (ETD passed with no onboard status), and missing BL alerts

### Requirement 17: Operations Tracking View

**User Story:** As an Operations_User, I want a consolidated tracking view of all shipments, so that I can monitor the progress of every active job in one place.

#### Acceptance Criteria

1. THE Platform SHALL display an Operations_View with the following columns: PI Number, Booking Number, Consignee, Shipping Line, Container Type, Vessel Name, Voyage, POL, POD, FPD, ETD, ETA, and Forwarder
2. THE Platform SHALL support filtering the Operations_View by: Customer, Shipping Line, Status, ETD date range, and Port of Loading
3. THE Platform SHALL support sorting the Operations_View by any displayed column
4. THE Platform SHALL paginate the Operations_View with a configurable page size defaulting to 25 records

### Requirement 18: Smart Automation - Invoice Auto-Fill

**User Story:** As an Accounts_User, I want the Commercial Invoice and Packing List to auto-fill from PI data, so that I avoid manual data re-entry and reduce errors.

#### Acceptance Criteria

1. WHEN a Commercial Invoice is created for a Booking linked to a Proforma Invoice, THE Platform SHALL auto-populate all product line items (Product Name, Quantity, Rate, Amount) from the Proforma Invoice
2. WHEN a Packing List is created for a Booking linked to a Proforma Invoice, THE Platform SHALL auto-populate product details from the Proforma Invoice
3. THE Platform SHALL allow users to edit auto-populated values before finalizing the document

### Requirement 19: Smart Automation - BL Auto-Fill

**User Story:** As an Operations_User, I want the BL Draft to auto-fill from the Commercial Invoice and Packing List, so that shipping documentation is consistent and complete.

#### Acceptance Criteria

1. WHEN a Bill of Lading is created for a Booking with a finalized Commercial Invoice and Packing List, THE Platform SHALL auto-populate: Container Number from the Booking containers, Vessel Name and Voyage from the Booking, Shipper and Consignee from the Booking master data references
2. THE Platform SHALL auto-populate cargo description on the BL from the Commercial Invoice product details
3. THE Platform SHALL allow users to edit auto-populated BL fields before submission

### Requirement 20: Smart Automation - Stock Deduction

**User Story:** As an Operations_User, I want stock to automatically deduct when I perform the stuffing action, so that inventory is always accurate without manual adjustment.

#### Acceptance Criteria

1. WHEN a Container is marked as "Stuffed," THE Automation_Engine SHALL identify the product quantities associated with the Container from the linked Proforma Invoice line items
2. WHEN a Container is marked as "Stuffed," THE Automation_Engine SHALL deduct each identified product quantity from the corresponding Stock_Item Available Stock
3. WHEN a Container is marked as "Stuffed," THE Automation_Engine SHALL add each identified product quantity to the corresponding Stock_Item Shipped Stock
4. IF the Automation_Engine encounters insufficient Available Stock during stuffing, THEN THE Platform SHALL reject the entire Stuffing_Action without partial deductions (atomic operation)

### Requirement 21: Email Notification Enhancement

**User Story:** As an Operations_User, I want booking confirmation emails to include PI data and onboard confirmations to include BL numbers, so that recipients have complete shipment context.

#### Acceptance Criteria

1. WHEN a Booking Confirmation email is sent for a Booking linked to a Proforma Invoice, THE Platform SHALL include the PI Number, Customer Name, and Total Amount in the email body
2. WHEN an Onboard Confirmation email is sent, THE Platform SHALL include: Serial Number, Booking Number, Container Number, Container Size, FPD, Shipping Line Name, and BL Number for each container in the Booking
3. THE Platform SHALL send notifications to a configurable distribution list in addition to the primary recipient
4. WHEN a payment is overdue (PI in Payment_Pending for more than 30 days), THE Platform SHALL send a payment reminder email to the customer

### Requirement 22: Role-Based Access Control for New Features

**User Story:** As an Admin_User, I want new features to respect role-based permissions, so that users only access functionality appropriate to their role.

#### Acceptance Criteria

1. THE Platform SHALL grant Admin_Users full read and write access to all new feature endpoints (Proforma Invoices, Payments, Stock Items, Commercial Invoices, Packing Lists, Bills of Lading, Dashboard, Operations View)
2. THE Platform SHALL grant Operations_Users read and write access to: Bookings, Containers, Stuffing Actions, Commercial Invoices, Packing Lists, Bills of Lading, and the Operations View
3. THE Platform SHALL grant Accounts_Users read and write access to: Proforma Invoices, Payments, Commercial Invoices, and Packing Lists
4. THE Platform SHALL grant Sales_Users read-only access to: Proforma Invoices and Shipment data filtered to clients assigned to the Sales_User via the Marketing Person relationship
5. IF a user without the required role attempts to access a restricted endpoint, THEN THE Platform SHALL return an HTTP 403 Forbidden response

### Requirement 23: Booking Status Extension for Shipment Tracking

**User Story:** As an Operations_User, I want extended booking statuses to reflect the shipment lifecycle, so that I can track each job from booking through delivery.

#### Acceptance Criteria

1. THE Platform SHALL extend the Booking status choices to include: Pending, Booked, Stuffing, Shipped, and Completed
2. THE Platform SHALL enforce the following Booking status transitions: Pending → Booked → Stuffing → Shipped → Completed
3. WHEN all Containers on a Booking are marked as "Stuffed," THE Platform SHALL allow transition to "Shipped" status
4. IF a user attempts to transition a Booking to "Shipped" while any Container has stuffing_status "Pending," THEN THE Platform SHALL reject the transition and return an error

### Requirement 24: Partial Shipment Support

**User Story:** As an Operations_User, I want one Proforma Invoice to link to multiple Bookings and Containers, so that I can split a large order across multiple shipments.

#### Acceptance Criteria

1. THE Platform SHALL allow one Proforma Invoice to be linked to multiple Bookings
2. THE Platform SHALL track which PI_Line_Items (or partial quantities thereof) are allocated to each Booking
3. THE Platform SHALL compute the total shipped quantity per PI_Line_Item as the sum of quantities across all linked Bookings
4. IF the total allocated quantity for a PI_Line_Item exceeds the original PI_Line_Item quantity, THEN THE Platform SHALL reject the allocation and return an error
5. THE Platform SHALL display the remaining unallocated quantity for each PI_Line_Item on the Proforma Invoice detail view
