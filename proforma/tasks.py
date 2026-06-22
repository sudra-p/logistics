"""
Celery tasks for proforma invoice automations.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from notifications.services import EmailNotificationService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def check_payment_overdue(self):
    """
    Daily Celery task that identifies Proforma Invoices in PAYMENT_PENDING
    status for more than 30 days and sends a reminder email via SES.
    """
    from proforma.models import ProformaInvoice

    threshold_date = timezone.now() - timedelta(days=30)

    overdue_pis = ProformaInvoice.objects.filter(
        status=ProformaInvoice.Status.PAYMENT_PENDING,
        updated_at__lte=threshold_date,
    ).select_related('customer')

    if not overdue_pis.exists():
        logger.info('check_payment_overdue: No overdue PIs found.')
        return

    service = EmailNotificationService()

    sent_count = 0
    failed_count = 0

    for pi in overdue_pis:
        try:
            service.send_payment_reminder(pi.id)
            sent_count += 1
        except Exception as e:
            failed_count += 1
            logger.error(
                'PI %s: Failed to send payment reminder email: %s',
                pi.pi_number,
                str(e),
            )

    logger.info(
        'check_payment_overdue: Completed. Sent=%d, Failed=%d.',
        sent_count,
        failed_count,
    )
