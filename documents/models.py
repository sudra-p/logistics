from django.conf import settings
from django.db import models


class Attachment(models.Model):
    """File attachment associated with a booking."""

    ALLOWED_MIME_TYPES = [
        'application/pdf',
        'image/jpeg',
        'image/png',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel',
    ]
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    MAX_ATTACHMENTS_PER_BOOKING = 20

    booking = models.ForeignKey(
        'bookings.Booking',
        on_delete=models.CASCADE,
        related_name='attachments',
    )
    filename = models.CharField(max_length=255)
    s3_key = models.CharField(max_length=500)
    file_size = models.PositiveIntegerField(help_text='File size in bytes')
    mime_type = models.CharField(max_length=100)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='uploaded_attachments',
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.filename} ({self.booking_id})"
