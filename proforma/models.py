from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


def generate_pi_number():
    """
    Generate a PI number in the format PI-YYYYMM-NNNN.
    Sequential numbering resets each month, zero-padded to 4 digits.
    """
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


class ProformaInvoice(models.Model):
    """Proforma Invoice for freight forwarding workflow."""

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
    customer = models.ForeignKey(
        'master_data.Client',
        on_delete=models.PROTECT,
        related_name='proforma_invoices',
    )
    currency = models.CharField(max_length=3, choices=Currency.choices)
    exchange_rate = models.DecimalField(
        max_digits=10, decimal_places=4, default=Decimal('1.0000')
    )
    payment_terms = models.TextField()
    expected_shipment_date = models.DateField()
    total_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00')
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='proforma_invoices_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-pi_number']

    def __str__(self):
        return f"{self.pi_number} - {self.customer}"

    def save(self, *args, **kwargs):
        # Auto-generate pi_number on creation
        if self.pk is None:
            self.pi_number = generate_pi_number()
        # Compute total_amount from line items (only if already saved)
        if self.pk is not None:
            self.total_amount = (
                self.line_items.aggregate(total=models.Sum('amount'))['total']
                or Decimal('0.00')
            )
        super().save(*args, **kwargs)


class ProformaLineItem(models.Model):
    """Line item within a Proforma Invoice."""

    proforma_invoice = models.ForeignKey(
        ProformaInvoice,
        on_delete=models.CASCADE,
        related_name='line_items',
    )
    product_name = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    rate = models.DecimalField(max_digits=12, decimal_places=2)
    amount = models.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        ordering = ['pk']

    def __str__(self):
        return f"{self.product_name} (qty: {self.quantity})"
