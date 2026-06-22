from django.conf import settings
from django.db import models


class Payment(models.Model):
    """Payment recorded against a Proforma Invoice."""

    class PaymentMode(models.TextChoices):
        BANK = 'BANK', 'Bank Transfer'
        CASH = 'CASH', 'Cash'
        LC = 'LC', 'Letter of Credit'

    proforma_invoice = models.ForeignKey(
        'proforma.ProformaInvoice',
        on_delete=models.PROTECT,
        related_name='payments',
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    payment_mode = models.CharField(max_length=10, choices=PaymentMode.choices)
    payment_date = models.DateField()
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='payments_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date', '-created_at']

    def __str__(self):
        return f"Payment {self.amount} for {self.proforma_invoice}"
