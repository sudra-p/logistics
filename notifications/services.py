"""
Email notification services for booking-related communications.
"""

import logging

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from bookings.models import Booking, CommunicationLog

logger = logging.getLogger(__name__)


class EmailNotificationService:
    """Service for sending booking-related email notifications via AWS SES."""

    def __init__(self):
        self.ses_client = boto3.client(
            'ses',
            region_name=settings.AWS_SES_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        self.from_email = settings.AWS_SES_FROM_EMAIL

    def _get_distribution_list(self):
        """Return the distribution list, filtering out empty strings."""
        return [
            email.strip()
            for email in settings.DISTRIBUTION_LIST
            if email.strip()
        ]

    def send_booking_confirmation(self, booking_id):
        """
        Send a booking confirmation email to the client and distribution list.

        Args:
            booking_id: ID of the booking to send confirmation for.

        Handles missing/invalid client email by logging the failure
        and still sending to the distribution list.
        """
        booking = Booking.objects.select_related(
            'client',
            'shipping_line',
            'pol',
            'pod',
            'por',
            'vessel',
        ).prefetch_related('containers__container_type').get(pk=booking_id)

        # Build recipient list
        distribution_list = self._get_distribution_list()
        client_email = getattr(booking.client, 'email', None)
        client_email_missing = not client_email or not client_email.strip()

        recipients = list(distribution_list)
        if not client_email_missing:
            recipients.insert(0, client_email.strip())

        # If client email is missing, log the failure
        if client_email_missing:
            logger.warning(
                'Booking %s: Client email is missing or invalid. '
                'Sending only to distribution list.',
                booking.job_number,
            )
            CommunicationLog.objects.create(
                booking=booking,
                email_type='booking_confirmation',
                recipients=distribution_list,
                status='partial',
                error_message='Client email is missing or invalid. Sent only to distribution list.',
            )

        # If no recipients at all, log failure and return
        if not recipients:
            logger.error(
                'Booking %s: No recipients available for booking confirmation email.',
                booking.job_number,
            )
            CommunicationLog.objects.create(
                booking=booking,
                email_type='booking_confirmation',
                recipients=[],
                status='failed',
                error_message='No recipients available (client email missing and distribution list empty).',
            )
            return

        # Build container summary
        container_summary = self._build_container_summary(booking)

        # Render email template
        subject = f"Booking Confirmation - {booking.booking_no or booking.job_number}"
        context = {
            'booking': booking,
            'booking_no': booking.booking_no or booking.job_number,
            'customer_name': booking.client.name if booking.client else 'TBD',
            'por': booking.por.name if booking.por else 'TBD',
            'pol': booking.pol.name if booking.pol else 'TBD',
            'pod': booking.pod.name if booking.pod else 'TBD',
            'stuffing_point': booking.stuffing_point or 'TBD',
            'clearance_point': booking.clearance_point or 'TBD',
            'container_summary': container_summary or 'TBD',
            'vessel_voyage': self._get_vessel_voyage(booking) or 'TBD',
            'shipping_line': booking.shipping_line.name if booking.shipping_line else 'TBD',
            'etd': booking.etd_pol.strftime('%d-%b-%Y %H:%M') if booking.etd_pol else 'TBD',
            'eta': booking.eta_destination.strftime('%d-%b-%Y %H:%M') if booking.eta_destination else 'TBD',
        }

        html_body = render_to_string(
            'notifications/booking_confirmation.html', context
        )

        # Send via SES
        try:
            self.ses_client.send_email(
                Source=self.from_email,
                Destination={'ToAddresses': recipients},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Html': {'Data': html_body, 'Charset': 'UTF-8'},
                    },
                },
            )
            # Log success
            CommunicationLog.objects.create(
                booking=booking,
                email_type='booking_confirmation',
                recipients=recipients,
                sent_at=timezone.now(),
                status='sent',
            )
            logger.info(
                'Booking %s: Booking confirmation email sent to %s.',
                booking.job_number,
                recipients,
            )
        except ClientError as e:
            # Log failure - let the caller (Celery task) handle retry
            logger.error(
                'Booking %s: Failed to send booking confirmation email: %s',
                booking.job_number,
                str(e),
            )
            raise

    def send_onboard_confirmation(self, booking_id):
        """
        Send an onboard confirmation email to the client and distribution list.

        Args:
            booking_id: ID of the booking to send onboard confirmation for.

        If client email is missing, skip the send entirely and log an error
        in CommunicationLog.
        """
        booking = Booking.objects.select_related(
            'client',
            'shipping_line',
            'pol',
            'pod',
            'fpd',
            'vessel',
        ).prefetch_related('containers').get(pk=booking_id)

        # Build recipient list
        distribution_list = self._get_distribution_list()
        client_email = getattr(booking.client, 'email', None)
        client_email_missing = not client_email or not client_email.strip()

        # If client email is missing: skip send entirely, log error
        if client_email_missing:
            logger.error(
                'Booking %s: Client email is missing. '
                'Skipping onboard confirmation email.',
                booking.job_number,
            )
            CommunicationLog.objects.create(
                booking=booking,
                email_type='onboard_confirmation',
                recipients=[],
                status='failed',
                error_message='Client email is missing. Onboard confirmation email not sent.',
            )
            return

        recipients = [client_email.strip()] + distribution_list

        # Build container data for table
        containers = booking.containers.all()
        container_rows = []
        for container in containers:
            container_rows.append({
                'booking_no': booking.booking_no or '',
                'container_no': container.container_no or '',
                'container_size': container.get_container_size_display() if container.container_size else '',
                'fpd': booking.fpd.name if booking.fpd else '',
                'shipping_line': booking.shipping_line.name if booking.shipping_line else '',
                'bl_no': booking.hbl_no or booking.mbl_no or '',
            })

        # Render email template
        subject = f"Onboard Confirmation - {booking.booking_no or booking.job_number}"
        context = {
            'booking': booking,
            'booking_no': booking.booking_no or booking.job_number,
            'customer_name': booking.client.name if booking.client else 'TBD',
            'container_rows': container_rows,
            'vessel_voyage': self._get_vessel_voyage(booking) or 'TBD',
        }

        html_body = render_to_string(
            'notifications/onboard_confirmation.html', context
        )

        # Send via SES
        try:
            self.ses_client.send_email(
                Source=self.from_email,
                Destination={'ToAddresses': recipients},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Html': {'Data': html_body, 'Charset': 'UTF-8'},
                    },
                },
            )
            # Log success
            CommunicationLog.objects.create(
                booking=booking,
                email_type='onboard_confirmation',
                recipients=recipients,
                sent_at=timezone.now(),
                status='sent',
            )
            logger.info(
                'Booking %s: Onboard confirmation email sent to %s.',
                booking.job_number,
                recipients,
            )
        except ClientError as e:
            # Log failure - let the caller (Celery task) handle retry
            logger.error(
                'Booking %s: Failed to send onboard confirmation email: %s',
                booking.job_number,
                str(e),
            )
            raise

    def _build_container_summary(self, booking):
        """
        Build a human-readable container summary like "2 x 20ft, 1 x 40ft HC".
        """
        containers = booking.containers.all()
        if not containers.exists():
            return ''

        summary_parts = []
        for container in containers:
            size_display = container.get_container_size_display()
            summary_parts.append(f"{container.container_count} x {size_display}")

        return ', '.join(summary_parts)

    def _get_vessel_voyage(self, booking):
        """Build vessel/voyage string."""
        parts = []
        if booking.vessel:
            parts.append(booking.vessel.name)
        if booking.voyage:
            parts.append(booking.voyage)
        return ' / '.join(parts) if parts else ''
