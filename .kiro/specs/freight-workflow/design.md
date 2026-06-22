# Design Document

## Overview

This design extends the existing logistics ERP platform with a complete freight forwarding workflow. The implementation adds new Django apps and models for Proforma Invoices, Payments, Stock Management, Commercial Invoices, Packing Lists, and Bills of Lading. The frontend is extended with new pages and components using the existing React + Tailwind + TanStack Query stack.

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                         │
│  (TanStack Query, React Router, Tailwind CSS)           │
├─────────────────────────────────────────────────────────┤
│              Django REST Framework API                    │
├──────────┬──────────┬──────────┬──────────┬─────────────┤
│ proforma │ payments │ inventory│ invoices │    bl       │
│   app    │   app    │   app    │   app    │   app       │
├──────────┴──────────┴──────────┴──────────┴─────────────┤
│              Existing Apps                                │
│  (accounts, bookings, documents, notifications,          │
│   master_data, search, reports)                          │
├─────────────────────────────────────────────────────────┤
│         PostgreSQL  │  Celery + Redis  │  AWS SES/S3    │
└─────────────────────────────────────────────────────────┘
```

### New Django Apps

1. **proforma** — Proforma Invoice and Line Items
2. **payments** — Payment recording and status tracking
3. **inventory** — Stock Item management and stuffing deduction
4. **invoices** — Commercial Invoice and Packing List
5. **bl** — Bill of Lading management

### Data Model Design

```
┌──────────────────┐     1:N      ┌──────────────────┐
│ ProformaInvoice  │─────────────▶│  ProformaLineItem│
│                  │              └──────────────────┘
│  pi_number       │
│  date            │     1:N      ┌──────────────────┐
│  customer (FK)   │─────────────▶│    Payment       │
│  currency        │              └──────────────────┘
│  exchange_rate   │
│  payment_terms   │     1:N      ┌──────────────────┐
│  expected_ship   │─────────────▶│    Booking       │
│  total_amount    │              │  (FK to PI)      │
│  status          │              └────────┬─────────┘
└──────────────────┘                       │
                                           │ 1:1
                               ┌───────────┼───────────┐
                               ▼           ▼           ▼
                    ┌──────────────┐ ┌──────────┐ ┌─────────┐
                    │CommercialInv │ │PackingList│ │   BL    │
                    └──────────────┘ └──────────┘ └─────────┘
                    
┌──────────────────┐
│   StockItem      │  (modified only on Container stuffing)
│  product_name    │
│  available_stock │
│  reserved_stock  │
│  shipped_stock   │
└──────────────────┘
```

## Database Models

### ProformaInvoice Model (proforma app)

```python
class ProformaInvoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SENT = 'SENT', 'Sent'
        APPROVED = 'APPROVED', 'Approved'
        PAYMENT_PENDING = 'PAYMENT_PENDING', 'Payment Pending'
        PAID = 'PAID', 'Paid'

    class Currency(models.TextChoices):
        USD = 'USD', 'US Dollar'
        INR = 'INR', 'Indian Rupee'

    pi_number = models.CharField(max_length=20, unique=True, editable=False)
    date = models.DateField()
    customer = models.ForeignKey('master_data.Client', on_delete=models.PROTECT)
    currency = models.CharField(max_length=3, choices=Currency.choices)
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4, default=1)
    payment_terms = models.TextField()
    expected_shipment_date = models.DateField()
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### ProformaLineItem Model (proforma app)

```python
class ProformaLineItem(models.Model):
    proforma_invoice = models.ForeignKey(ProformaInvoice, on_delete=models.CASCADE, related_name='line_items')
    product_name = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    rate = models.DecimalField(max_digits=12, decimal_places=2)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
```

### Payment Model (payments app)

```python
class Payment(models.Model):
    class PaymentMode(models.TextChoices):
        BANK = 'BANK', 'Bank Transfer'
        CASH = 'CASH', 'Cash'
        LC = 'LC', 'Letter of Credit'

    proforma_invoice = models.ForeignKey('proforma.ProformaInvoice', on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    payment_mode = models.CharField(max_length=10, choices=PaymentMode.choices)
    payment_date = models.DateField()
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
```

### StockItem Model (inventory app)

```python
class StockItem(models.Model):
    product_name = models.CharField(max_length=255, unique=True)
    available_stock = models.PositiveIntegerField(default=0)
    reserved_stock = models.PositiveIntegerField(default=0)
    shipped_stock = models.PositiveIntegerField(default=0)
    unit = models.CharField(max_length=50, default='units')
    updated_at = models.DateTimeField(auto_now=True)
```

### CommercialInvoice Model (invoices app)

```python
class CommercialInvoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        FINALIZED = 'FINALIZED', 'Finalized'

    booking = models.ForeignKey('bookings.Booking', on_delete=models.PROTECT, related_name='commercial_invoices')
    invoice_number = models.CharField(max_length=30, unique=True)
    revision = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class CommercialInvoiceLineItem(models.Model):
    commercial_invoice = models.ForeignKey(CommercialInvoice, on_delete=models.CASCADE, related_name='line_items')
    product_name = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    rate = models.DecimalField(max_digits=12, decimal_places=2)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    net_weight = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    gross_weight = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    hs_code = models.CharField(max_length=20, blank=True)
    num_packages = models.PositiveIntegerField(null=True)
```

### PackingList Model (invoices app)

```python
class PackingList(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        FINALIZED = 'FINALIZED', 'Finalized'

    booking = models.ForeignKey('bookings.Booking', on_delete=models.PROTECT, related_name='packing_lists')
    packing_list_number = models.CharField(max_length=30, unique=True)
    revision = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class PackingListLineItem(models.Model):
    packing_list = models.ForeignKey(PackingList, on_delete=models.CASCADE, related_name='line_items')
    product_name = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    num_packages = models.PositiveIntegerField()
    net_weight = models.DecimalField(max_digits=10, decimal_places=3)
    gross_weight = models.DecimalField(max_digits=10, decimal_places=3)
    package_type = models.CharField(max_length=100)
```

### BillOfLading Model (bl app)

```python
class BillOfLading(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SUBMITTED = 'SUBMITTED', 'Submitted'
        RELEASED = 'RELEASED', 'Released'

    class BLType(models.TextChoices):
        LINE = 'LINE', 'Line BL'
        DIRECT = 'DIRECT', 'Direct BL'

    booking = models.ForeignKey('bookings.Booking', on_delete=models.PROTECT, related_name='bills_of_lading')
    bl_number = models.CharField(max_length=50, unique=True)
    bl_type = models.CharField(max_length=10, choices=BLType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    container_number = models.CharField(max_length=50)
    vessel_name = models.CharField(max_length=255)
    voyage_number = models.CharField(max_length=100)
    shipper = models.ForeignKey('master_data.Shipper', on_delete=models.PROTECT)
    consignee = models.ForeignKey('master_data.Consignee', on_delete=models.PROTECT)
    notify_party = models.TextField(blank=True)
    cargo_description = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### Booking Model Modifications

```python
# Add to existing Booking model:
class Status(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    BOOKED = 'BOOKED', 'Booked'
    STUFFING = 'STUFFING', 'Stuffing'
    SHIPPED = 'SHIPPED', 'Shipped'
    COMPLETED = 'COMPLETED', 'Completed'

# New FK field:
proforma_invoice = models.ForeignKey('proforma.ProformaInvoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')

# Container model addition:
class StuffingStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    STUFFED = 'STUFFED', 'Stuffed'

stuffing_status = models.CharField(max_length=10, choices=StuffingStatus.choices, default=StuffingStatus.PENDING)
stuffed_at = models.DateTimeField(null=True, blank=True)
stuffed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
```

## API Endpoints

### Proforma Invoice Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| POST | /api/proforma-invoices/ | Create PI | Accounts, Admin |
| GET | /api/proforma-invoices/ | List PIs | Accounts, Admin, Sales (filtered) |
| GET | /api/proforma-invoices/{id}/ | Get PI detail | Accounts, Admin, Sales (filtered) |
| PATCH | /api/proforma-invoices/{id}/ | Update PI | Accounts, Admin |
| PATCH | /api/proforma-invoices/{id}/status/ | Change PI status | Accounts, Admin |
| GET | /api/proforma-invoices/{id}/bookings/ | List linked bookings | All authenticated |

### Payment Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| POST | /api/payments/ | Create payment | Accounts, Admin |
| GET | /api/payments/ | List payments | Accounts, Admin |
| GET | /api/payments/?proforma_invoice={id} | Filter by PI | Accounts, Admin |
| GET | /api/proforma-invoices/{id}/payments/ | Payments for a PI | Accounts, Admin |

### Stock/Inventory Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| POST | /api/stock-items/ | Create stock item | Operations, Admin |
| GET | /api/stock-items/ | List stock items | Operations, Admin |
| PATCH | /api/stock-items/{id}/ | Update stock item | Operations, Admin |
| POST | /api/bookings/{id}/containers/{cid}/stuff/ | Mark container stuffed | Operations, Admin |

### Commercial Invoice & Packing List Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| POST | /api/bookings/{id}/commercial-invoice/ | Create invoice | Accounts, Operations, Admin |
| GET | /api/bookings/{id}/commercial-invoice/ | Get invoice | All authenticated |
| PATCH | /api/commercial-invoices/{id}/ | Update invoice | Accounts, Operations, Admin |
| PATCH | /api/commercial-invoices/{id}/finalize/ | Finalize invoice | Accounts, Operations, Admin |
| POST | /api/bookings/{id}/packing-list/ | Create packing list | Accounts, Operations, Admin |
| GET | /api/bookings/{id}/packing-list/ | Get packing list | All authenticated |
| PATCH | /api/packing-lists/{id}/ | Update packing list | Accounts, Operations, Admin |
| PATCH | /api/packing-lists/{id}/finalize/ | Finalize packing list | Accounts, Operations, Admin |

### Bill of Lading Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| POST | /api/bookings/{id}/bl/ | Create BL | Operations, Admin |
| GET | /api/bookings/{id}/bl/ | Get BL for booking | All authenticated |
| PATCH | /api/bl/{id}/ | Update BL | Operations, Admin |
| PATCH | /api/bl/{id}/status/ | Change BL status | Operations, Admin |

### Dashboard Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | /api/dashboard/kpis/ | Get KPI card data | All authenticated |
| GET | /api/dashboard/proforma-status/ | Proforma status section | All authenticated |
| GET | /api/dashboard/ready-for-booking/ | Ready for booking PIs | Operations, Admin |
| GET | /api/dashboard/current-shipments/ | Active shipments | All authenticated |
| GET | /api/dashboard/document-status/ | Document status counts | All authenticated |
| GET | /api/dashboard/alerts/ | Active alerts | All authenticated |

### Operations View Endpoint

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | /api/operations/ | Operations tracking view | Operations, Admin |

## Frontend Structure

### New Pages

```
frontend/src/features/
├── proforma/
│   ├── ProformaListPage.tsx
│   ├── ProformaFormPage.tsx
│   ├── ProformaDetailPage.tsx
│   └── components/
│       ├── PIStatusBadge.tsx
│       ├── LineItemTable.tsx
│       └── PaymentSummary.tsx
├── payments/
│   ├── PaymentListPage.tsx
│   ├── PaymentFormPage.tsx
│   └── components/
│       └── PaymentStatusBadge.tsx
├── inventory/
│   ├── StockListPage.tsx
│   ├── StockFormPage.tsx
│   └── components/
│       └── StockLevelIndicator.tsx
├── invoices/
│   ├── CommercialInvoicePage.tsx
│   ├── PackingListPage.tsx
│   └── components/
│       ├── InvoiceLineItemTable.tsx
│       └── DocumentVersionHistory.tsx
├── bl/
│   ├── BLFormPage.tsx
│   ├── BLDetailPage.tsx
│   └── components/
│       ├── BLStatusBadge.tsx
│       └── BLAutoFillPreview.tsx
├── dashboard/
│   ├── DashboardPage.tsx
│   └── components/
│       ├── KPICard.tsx
│       ├── ProformaStatusSection.tsx
│       ├── ReadyForBookingSection.tsx
│       ├── CurrentShipmentsSection.tsx
│       ├── DocumentStatusSection.tsx
│       └── AlertsSection.tsx
└── operations/
    ├── OperationsPage.tsx
    └── components/
        └── OperationsTable.tsx
```

## Key Service Logic

### PI Number Generation

```python
def generate_pi_number():
    """Generate PI-YYYYMM-NNNN format number."""
    from django.utils import timezone
    now = timezone.now()
    prefix = f"PI-{now.strftime('%Y%m')}-"
    last_pi = ProformaInvoice.objects.filter(
        pi_number__startswith=prefix
    ).order_by('-pi_number').first()
    
    if last_pi:
        last_seq = int(last_pi.pi_number.split('-')[-1])
        next_seq = last_seq + 1
    else:
        next_seq = 1
    
    return f"{prefix}{next_seq:04d}"
```

### Payment Status Computation

```python
def compute_payment_status(proforma_invoice):
    """Determine payment status from total payments vs PI amount."""
    total_paid = proforma_invoice.payments.aggregate(
        total=models.Sum('amount')
    )['total'] or Decimal('0')
    
    if total_paid >= proforma_invoice.total_amount:
        return 'Fully_Paid'
    elif total_paid > 0:
        return 'Partial_Paid'
    return 'Unpaid'
```

### Stuffing Action (Atomic Stock Deduction)

```python
@transaction.atomic
def perform_stuffing(container_id, product_quantities, user):
    """
    Mark container as stuffed and deduct stock atomically.
    product_quantities: [{product_name: str, quantity: int}, ...]
    """
    container = Container.objects.select_for_update().get(pk=container_id)
    
    if container.stuffing_status == 'STUFFED':
        raise ValidationError("Container is already stuffed.")
    
    # Validate and deduct stock
    for item in product_quantities:
        stock = StockItem.objects.select_for_update().get(
            product_name=item['product_name']
        )
        if stock.available_stock < item['quantity']:
            raise ValidationError(
                f"Insufficient stock for {item['product_name']}: "
                f"available={stock.available_stock}, requested={item['quantity']}"
            )
        stock.available_stock -= item['quantity']
        stock.shipped_stock += item['quantity']
        stock.save()
    
    # Update container status
    container.stuffing_status = 'STUFFED'
    container.stuffed_at = timezone.now()
    container.stuffed_by = user
    container.save()
```

### Status Transition Validation

```python
PI_TRANSITIONS = {
    'DRAFT': ['SENT'],
    'SENT': ['APPROVED'],
    'APPROVED': ['PAYMENT_PENDING'],
    'PAYMENT_PENDING': ['PAID'],
    'PAID': [],
}

BOOKING_TRANSITIONS = {
    'PENDING': ['BOOKED'],
    'BOOKED': ['STUFFING'],
    'STUFFING': ['SHIPPED'],
    'SHIPPED': ['COMPLETED'],
    'COMPLETED': [],
}

BL_TRANSITIONS = {
    'DRAFT': ['SUBMITTED'],
    'SUBMITTED': ['RELEASED'],
    'RELEASED': [],
}

def validate_status_transition(current, new, transitions_map):
    """Validate that a status transition is allowed."""
    allowed = transitions_map.get(current, [])
    if new not in allowed:
        raise ValidationError(
            f"Cannot transition from {current} to {new}. "
            f"Allowed transitions: {allowed}"
        )
```

## Correctness Properties

### Property 1: PI Total Amount Equals Sum of Line Items
- For any ProformaInvoice, `total_amount == sum(line_item.amount for line_item in line_items)`
- `line_item.amount == line_item.quantity * line_item.rate` for each line item

### Property 2: Payment Amount Never Exceeds PI Total
- For any ProformaInvoice, `sum(payment.amount for payment in payments) <= total_amount`

### Property 3: Stock Conservation (Invariant)
- For any StockItem, the sum of `available_stock + shipped_stock` represents total inventory
- Stuffing action: `available_stock_before - quantity == available_stock_after` AND `shipped_stock_before + quantity == shipped_stock_after`

### Property 4: Status Transition Validity
- For ProformaInvoice, Booking, and BillOfLading: transitions only follow defined adjacency maps
- No status can transition to itself
- No backward transitions are possible

### Property 5: Stuffing Atomicity
- If any product has insufficient stock, NO stock items are modified (all-or-nothing)
- Container remains in PENDING status if any deduction fails

### Property 6: Partial Shipment Allocation
- For any PI_Line_Item, `sum(allocated_qty across all bookings) <= original_qty`
- Remaining unallocated quantity is non-negative

### Property 7: Role-Based Access Enforcement
- Sales_Users can only read PIs/Bookings linked to their assigned clients (via Marketing Person)
- Accounts_Users cannot perform stuffing actions
- Operations_Users cannot create payments

### Property 8: PI Number Uniqueness and Format
- All PI numbers match the pattern `PI-YYYYMM-NNNN`
- No two ProformaInvoices share the same pi_number
- Sequential generation within a month produces monotonically increasing suffixes

### Property 9: Document Versioning Idempotence
- Finalizing an already-finalized document creates a new revision (revision + 1)
- The previous revision remains immutable
- Revision numbers are monotonically increasing per document

### Property 10: Auto-Fill Round-Trip Consistency
- Data auto-filled from PI to Commercial Invoice preserves: product_name, quantity, rate, amount
- Data auto-filled from Booking to BL preserves: vessel_name, voyage, container_number, shipper, consignee
