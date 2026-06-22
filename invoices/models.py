from django.conf import settings
from django.db import models
from django.utils import timezone


def generate_invoice_number():
    """
    Generate an invoice number in the format INV-YYYYMM-NNNN.
    Sequential numbering resets each month, zero-padded to 4 digits.
    """
    now = timezone.now()
    prefix = f"INV-{now.strftime('%Y%m')}-"
    last_inv = CommercialInvoice.objects.filter(
        invoice_number__startswith=prefix
    ).order_by('-invoice_number').first()

    if last_inv:
        last_seq = int(last_inv.invoice_number.split('-')[-1])
        next_seq = last_seq + 1
    else:
        next_seq = 1

    return f"{prefix}{next_seq:04d}"


def generate_packing_list_number():
    """
    Generate a packing list number in the format PL-YYYYMM-NNNN.
    Sequential numbering resets each month, zero-padded to 4 digits.
    """
    now = timezone.now()
    prefix = f"PL-{now.strftime('%Y%m')}-"
    last_pl = PackingList.objects.filter(
        packing_list_number__startswith=prefix
    ).order_by('-packing_list_number').first()

    if last_pl:
        last_seq = int(last_pl.packing_list_number.split('-')[-1])
        next_seq = last_seq + 1
    else:
        next_seq = 1

    return f"{prefix}{next_seq:04d}"


class CommercialInvoice(models.Model):
    """Commercial Invoice linked to a booking."""

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        FINALIZED = 'FINALIZED', 'Finalized'

    booking = models.ForeignKey(
        'bookings.Booking',
        on_delete=models.PROTECT,
        related_name='commercial_invoices',
    )
    invoice_number = models.CharField(max_length=30, unique=True, editable=False)
    revision = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='commercial_invoices_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.invoice_number} (rev {self.revision})"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = generate_invoice_number()
        super().save(*args, **kwargs)


class CommercialInvoiceLineItem(models.Model):
    """Line item within a Commercial Invoice."""

    commercial_invoice = models.ForeignKey(
        CommercialInvoice,
        on_delete=models.CASCADE,
        related_name='line_items',
    )
    product_name = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    rate = models.DecimalField(max_digits=12, decimal_places=2)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    net_weight = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    gross_weight = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    hs_code = models.CharField(max_length=20, blank=True)
    num_packages = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['pk']

    def __str__(self):
        return f"{self.product_name} (qty: {self.quantity})"


class PackingList(models.Model):
    """Packing List linked to a booking."""

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        FINALIZED = 'FINALIZED', 'Finalized'

    booking = models.ForeignKey(
        'bookings.Booking',
        on_delete=models.PROTECT,
        related_name='packing_lists',
    )
    packing_list_number = models.CharField(max_length=30, unique=True, editable=False)
    revision = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='packing_lists_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.packing_list_number} (rev {self.revision})"

    def save(self, *args, **kwargs):
        if not self.packing_list_number:
            self.packing_list_number = generate_packing_list_number()
        super().save(*args, **kwargs)


class PackingListLineItem(models.Model):
    """Line item within a Packing List."""

    packing_list = models.ForeignKey(
        PackingList,
        on_delete=models.CASCADE,
        related_name='line_items',
    )
    product_name = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    num_packages = models.PositiveIntegerField()
    net_weight = models.DecimalField(max_digits=10, decimal_places=3)
    gross_weight = models.DecimalField(max_digits=10, decimal_places=3)
    package_type = models.CharField(max_length=100)

    class Meta:
        ordering = ['pk']

    def __str__(self):
        return f"{self.product_name} (qty: {self.quantity})"
