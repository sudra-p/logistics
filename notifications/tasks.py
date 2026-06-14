"""
Celery tasks for email notifications with retry logic.
"""

import logging

from botocore.exceptions import ClientError
from celery import shared_task
from django.utils import timezone

from bookings.models import Booking, CommunicationLog

logger = logging.getLogger(__name__)

# Exponential backoff delays in seconds: 30s, 60s, 120s
RETRY_DELAYS = [30, 60, 120]


@shared_task(bind=True, max_retries=3)
def send_onboard_confirmation_task(self, booking_id):
    """
    Celery task to send onboard confirmation email with retry logic.

    Retries up to 3 times with exponential backoff (30s, 60s, 120s).
    On final failure, logs the error in CommunicationLog.

    Args:
        booking_id: ID of the booking to send onboard confirmation for.
    """
    from notifications.services import EmailNotificationService

    try:
        service = EmailNotificationService()
        service.send_onboard_confirmation(booking_id)
    except ClientError as exc:
        retry_number = self.request.retries
        if retry_number < self.max_retries:
            countdown = RETRY_DELAYS[retry_number]
            logger.warning(
                'Booking %s: Retrying onboard confirmation email '
                '(attempt %d/%d) in %ds.',
                booking_id,
                retry_number + 1,
                self.max_retries,
                countdown,
            )
            raise self.retry(exc=exc, countdown=countdown)
        else:
            logger.error(
                'Booking %s: All retries exhausted for onboard confirmation email. '
                'Error: %s',
                booking_id,
                str(exc),
            )
            try:
                booking = Booking.objects.get(pk=booking_id)
                CommunicationLog.objects.create(
                    booking=booking,
                    email_type='onboard_confirmation',
                    recipients=[],
                    status='failed',
                    error_message=f'All retries exhausted. Last error: {str(exc)}',
                )
            except Booking.DoesNotExist:
                logger.error(
                    'Booking %s not found when logging final onboard email failure.',
                    booking_id,
                )
    except Booking.DoesNotExist:
        logger.error(
            'Booking %s not found. Cannot send onboard confirmation email.',
            booking_id,
        )
    except Exception as exc:
        retry_number = self.request.retries
        if retry_number < self.max_retries:
            countdown = RETRY_DELAYS[retry_number]
            logger.warning(
                'Booking %s: Unexpected error sending onboard confirmation email. '
                'Retrying (attempt %d/%d) in %ds. Error: %s',
                booking_id,
                retry_number + 1,
                self.max_retries,
                countdown,
                str(exc),
            )
            raise self.retry(exc=exc, countdown=countdown)
        else:
            logger.error(
                'Booking %s: All retries exhausted for onboard confirmation email. '
                'Unexpected error: %s',
                booking_id,
                str(exc),
            )
            try:
                booking = Booking.objects.get(pk=booking_id)
                CommunicationLog.objects.create(
                    booking=booking,
                    email_type='onboard_confirmation',
                    recipients=[],
                    status='failed',
                    error_message=f'All retries exhausted. Last error: {str(exc)}',
                )
            except Booking.DoesNotExist:
                logger.error(
                    'Booking %s not found when logging final onboard email failure.',
                    booking_id,
                )


@shared_task(bind=True, max_retries=3)
def send_booking_confirmation_task(self, booking_id):
    """
    Celery task to send booking confirmation email with retry logic.

    Retries up to 3 times with exponential backoff (30s, 60s, 120s).
    On final failure, logs the error in CommunicationLog.

    Args:
        booking_id: ID of the booking to send confirmation for.
    """
    from notifications.services import EmailNotificationService

    try:
        service = EmailNotificationService()
        service.send_booking_confirmation(booking_id)
    except ClientError as exc:
        # Determine retry countdown based on current attempt
        retry_number = self.request.retries
        if retry_number < self.max_retries:
            countdown = RETRY_DELAYS[retry_number]
            logger.warning(
                'Booking %s: Retrying booking confirmation email '
                '(attempt %d/%d) in %ds.',
                booking_id,
                retry_number + 1,
                self.max_retries,
                countdown,
            )
            raise self.retry(exc=exc, countdown=countdown)
        else:
            # Final failure - log to CommunicationLog
            logger.error(
                'Booking %s: All retries exhausted for booking confirmation email. '
                'Error: %s',
                booking_id,
                str(exc),
            )
            try:
                booking = Booking.objects.get(pk=booking_id)
                CommunicationLog.objects.create(
                    booking=booking,
                    email_type='booking_confirmation',
                    recipients=[],
                    status='failed',
                    error_message=f'All retries exhausted. Last error: {str(exc)}',
                )
            except Booking.DoesNotExist:
                logger.error(
                    'Booking %s not found when logging final email failure.',
                    booking_id,
                )
    except Booking.DoesNotExist:
        logger.error(
            'Booking %s not found. Cannot send confirmation email.',
            booking_id,
        )
    except Exception as exc:
        # Unexpected error - retry with same backoff logic
        retry_number = self.request.retries
        if retry_number < self.max_retries:
            countdown = RETRY_DELAYS[retry_number]
            logger.warning(
                'Booking %s: Unexpected error sending confirmation email. '
                'Retrying (attempt %d/%d) in %ds. Error: %s',
                booking_id,
                retry_number + 1,
                self.max_retries,
                countdown,
                str(exc),
            )
            raise self.retry(exc=exc, countdown=countdown)
        else:
            logger.error(
                'Booking %s: All retries exhausted for booking confirmation email. '
                'Unexpected error: %s',
                booking_id,
                str(exc),
            )
            try:
                booking = Booking.objects.get(pk=booking_id)
                CommunicationLog.objects.create(
                    booking=booking,
                    email_type='booking_confirmation',
                    recipients=[],
                    status='failed',
                    error_message=f'All retries exhausted. Last error: {str(exc)}',
                )
            except Booking.DoesNotExist:
                logger.error(
                    'Booking %s not found when logging final email failure.',
                    booking_id,
                )
