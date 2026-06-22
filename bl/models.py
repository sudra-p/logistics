from django.conf import settings
from django.db import models


class BillOfLading(models.Model):
    """Bill of Lading linked to a booking."""

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SUBMITTED = 'SUBMITTED', 'Submitted'
        RELEASED = 'RELEASED', 'Released'

    class BLType(models.TextChoices):
        LINE = 'LINE', 'Line BL'
        DIRECT = 'DIRECT', 'Direct BL'

    booking = models.ForeignKey(
        'bookings.Booking',
        on_delete=models.PROTECT,
        related_name='bills_of_lading',
    )
    bl_number = models.CharField(max_length=50, unique=True)
    bl_type = models.CharField(max_length=10, choices=BLType.choices)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    container_number = models.CharField(max_length=50)
    vessel_name = models.CharField(max_length=255)
    voyage_number = models.CharField(max_length=100)
    shipper = models.ForeignKey(
        'master_data.Shipper',
        on_delete=models.PROTECT,
        related_name='bills_of_lading',
    )
    consignee = models.ForeignKey(
        'master_data.Consignee',
        on_delete=models.PROTECT,
        related_name='bills_of_lading',
    )
    notify_party = models.TextField(blank=True)
    cargo_description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='bills_of_lading_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Bill of Lading'
        verbose_name_plural = 'Bills of Lading'

    def __str__(self):
        return f"{self.bl_number} ({self.booking.job_number})"
