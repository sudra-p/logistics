"""
Celery tasks for Bill of Lading automations.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def check_pending_bl(self):
    """
    Daily Celery task that identifies Bookings with status SHIPPED where:
    - No Bill of Lading exists, OR
    - The Bill of Lading is still in DRAFT status
    AND it has been more than 7 days after the Booking's ETD.

    Creates alert records in the Alert model for each matching booking.
    """
    from bl.models import BillOfLading
    from bookings.models import Booking
    from dashboard.models import Alert

    now = timezone.now()
    seven_days_ago = now - timedelta(days=7)

    # Find shipped bookings where ETD was more than 7 days ago
    shipped_bookings = Booking.objects.filter(
        status=Booking.Status.SHIPPED,
        etd_pol__lte=seven_days_ago,
    ).select_related('client')

    created_count = 0

    for booking in shipped_bookings:
        # Check BL status for this booking
        bls = BillOfLading.objects.filter(booking=booking)

        if not bls.exists():
            # No BL at all — create "Missing BL" alert
            alert_type = Alert.AlertType.MISSING_BL
            message = (
                f"Booking {booking.job_number} for {booking.client.name} "
                f"is shipped but has no Bill of Lading "
                f"(ETD was {booking.etd_pol.strftime('%Y-%m-%d')})"
            )
        elif bls.filter(status=BillOfLading.Status.DRAFT).exists() and \
                not bls.exclude(status=BillOfLading.Status.DRAFT).exists():
            # All BLs are still in DRAFT — create "Pending BL" alert
            alert_type = Alert.AlertType.PENDING_BL
            message = (
                f"Booking {booking.job_number} for {booking.client.name} "
                f"has Bill of Lading still in DRAFT status more than 7 days "
                f"after ETD ({booking.etd_pol.strftime('%Y-%m-%d')})"
            )
        else:
            # BL exists and is not all-DRAFT (SUBMITTED or RELEASED) — no alert needed
            continue

        # Avoid creating duplicate unresolved alerts for the same booking
        existing_alert = Alert.objects.filter(
            alert_type=alert_type,
            related_object_id=booking.pk,
            related_object_type='booking',
            is_resolved=False,
        ).exists()

        if not existing_alert:
            Alert.objects.create(
                alert_type=alert_type,
                message=message,
                related_object_id=booking.pk,
                related_object_type='booking',
            )
            created_count += 1
            logger.info(
                'Created %s alert for booking %s.',
                alert_type,
                booking.job_number,
            )

    logger.info(
        'check_pending_bl: Completed. Created %d alert(s).',
        created_count,
    )
