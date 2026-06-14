"""
Tests for the booking confirmation email notification feature.

Covers:
- Email template rendering with all fields
- "TBD" displayed for missing fields
- CommunicationLog created on success
- CommunicationLog created with error on failure
- Missing client email handled (still sends to distribution list)
- Celery task retry logic
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import TestCase, override_settings

from bookings.models import Booking, CommunicationLog, Container
from master_data.models import (
    Client,
    Commodity,
    ContainerType,
    Port,
    ShippingLine,
    Vessel,
)
from notifications.services import EmailNotificationService
from notifications.tasks import send_booking_confirmation_task

User = get_user_model()


@pytest.mark.django_db
class TestBookingConfirmationEmail(TestCase):
    """Tests for the booking confirmation email service."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testops', password='testpass123'
        )
        self.client_entity = Client.objects.create(
            name='Test Client', email='client@example.com'
        )
        self.shipping_line = ShippingLine.objects.create(
            name='Maersk', code='MAEU'
        )
        self.pol = Port.objects.create(name='Mumbai', code='INMUN', country='India')
        self.pod = Port.objects.create(name='Rotterdam', code='NLRTM', country='Netherlands')
        self.por = Port.objects.create(name='Delhi ICD', code='INDEL', country='India')
        self.commodity = Commodity.objects.create(name='Electronics', hs_code='8471')
        self.vessel = Vessel.objects.create(name='MSC Oscar', imo_number='9703318')
        self.container_type = ContainerType.objects.create(name='Dry', code='DRY')

        self.booking = Booking.objects.create(
            booking_no='BK-001',
            booking_date=date.today(),
            booking_validity_date=date.today() + timedelta(days=30),
            forwarding_window_start=date.today(),
            forwarding_window_end=date.today() + timedelta(days=14),
            shipping_line=self.shipping_line,
            pol=self.pol,
            pod=self.pod,
            por=self.por,
            client=self.client_entity,
            commodity=self.commodity,
            vessel=self.vessel,
            voyage='V001',
            cargo_type=Booking.CargoType.FCL,
            shipment_type='Export',
            stuffing_type='Factory',
            stuffing_point='Mumbai CFS',
            clearance_point='Nhava Sheva',
            created_by=self.user,
        )

        # Add a container
        Container.objects.create(
            booking=self.booking,
            container_type=self.container_type,
            container_size='20FT',
            container_count=2,
        )

    @override_settings(
        DISTRIBUTION_LIST=['ops@company.com', 'cs@company.com'],
        AWS_SES_FROM_EMAIL='noreply@logistics.example.com',
        AWS_SES_REGION='ap-south-1',
        AWS_ACCESS_KEY_ID='test-key',
        AWS_SECRET_ACCESS_KEY='test-secret',
    )
    @patch('notifications.services.boto3.client')
    def test_send_booking_confirmation_success(self, mock_boto_client):
        """Test successful booking confirmation email."""
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses

        service = EmailNotificationService()
        service.send_booking_confirmation(self.booking.id)

        # Verify SES was called
        mock_ses.send_email.assert_called_once()
        call_kwargs = mock_ses.send_email.call_args[1]

        # Verify recipients include client + distribution list
        recipients = call_kwargs['Destination']['ToAddresses']
        assert 'client@example.com' in recipients
        assert 'ops@company.com' in recipients
        assert 'cs@company.com' in recipients

        # Verify subject
        assert 'BK-001' in call_kwargs['Message']['Subject']['Data']

        # Verify CommunicationLog created
        log = CommunicationLog.objects.filter(
            booking=self.booking, email_type='booking_confirmation'
        ).last()
        assert log is not None
        assert log.status == 'sent'
        assert log.sent_at is not None
        assert 'client@example.com' in log.recipients

    @override_settings(
        DISTRIBUTION_LIST=['ops@company.com'],
        AWS_SES_FROM_EMAIL='noreply@logistics.example.com',
        AWS_SES_REGION='ap-south-1',
        AWS_ACCESS_KEY_ID='test-key',
        AWS_SECRET_ACCESS_KEY='test-secret',
    )
    @patch('notifications.services.boto3.client')
    def test_template_renders_all_fields(self, mock_boto_client):
        """Test that the email template includes all required fields."""
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses

        service = EmailNotificationService()
        service.send_booking_confirmation(self.booking.id)

        call_kwargs = mock_ses.send_email.call_args[1]
        html_body = call_kwargs['Message']['Body']['Html']['Data']

        # Verify all required fields are present
        assert 'BK-001' in html_body  # Booking No
        assert 'Test Client' in html_body  # Customer name
        assert 'Delhi ICD' in html_body  # POR
        assert 'Mumbai' in html_body  # POL
        assert 'Rotterdam' in html_body  # POD
        assert 'Mumbai CFS' in html_body  # Stuffing Point
        assert 'Nhava Sheva' in html_body  # Clearance Point
        assert '2 x 20ft' in html_body  # Container summary
        assert 'MSC Oscar' in html_body  # Vessel
        assert 'V001' in html_body  # Voyage
        assert 'Maersk' in html_body  # Shipping Line

    @override_settings(
        DISTRIBUTION_LIST=['ops@company.com'],
        AWS_SES_FROM_EMAIL='noreply@logistics.example.com',
        AWS_SES_REGION='ap-south-1',
        AWS_ACCESS_KEY_ID='test-key',
        AWS_SECRET_ACCESS_KEY='test-secret',
    )
    @patch('notifications.services.boto3.client')
    def test_tbd_displayed_for_missing_fields(self, mock_boto_client):
        """Test that TBD is shown for missing/null field values."""
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses

        # Create booking without optional fields
        booking_minimal = Booking.objects.create(
            booking_no='',
            booking_date=date.today(),
            booking_validity_date=date.today() + timedelta(days=30),
            forwarding_window_start=date.today(),
            forwarding_window_end=date.today() + timedelta(days=14),
            shipping_line=self.shipping_line,
            pol=self.pol,
            pod=self.pod,
            client=self.client_entity,
            commodity=self.commodity,
            cargo_type=Booking.CargoType.FCL,
            shipment_type='Export',
            stuffing_type='Factory',
            created_by=self.user,
        )

        service = EmailNotificationService()
        service.send_booking_confirmation(booking_minimal.id)

        call_kwargs = mock_ses.send_email.call_args[1]
        html_body = call_kwargs['Message']['Body']['Html']['Data']

        # Fields that should show TBD
        # POR is not set, Stuffing Point is empty, Clearance Point is empty,
        # Vessel/Voyage is empty, ETD/ETA are null
        assert 'TBD' in html_body

    @override_settings(
        DISTRIBUTION_LIST=['ops@company.com', 'cs@company.com'],
        AWS_SES_FROM_EMAIL='noreply@logistics.example.com',
        AWS_SES_REGION='ap-south-1',
        AWS_ACCESS_KEY_ID='test-key',
        AWS_SECRET_ACCESS_KEY='test-secret',
    )
    @patch('notifications.services.boto3.client')
    def test_missing_client_email_sends_to_distribution_list(self, mock_boto_client):
        """Test that missing client email still sends to distribution list."""
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses

        # Set client email to empty
        self.client_entity.email = ''
        self.client_entity.save()

        service = EmailNotificationService()
        service.send_booking_confirmation(self.booking.id)

        # Verify SES was still called
        mock_ses.send_email.assert_called_once()
        call_kwargs = mock_ses.send_email.call_args[1]
        recipients = call_kwargs['Destination']['ToAddresses']

        # Should only contain distribution list
        assert 'ops@company.com' in recipients
        assert 'cs@company.com' in recipients
        assert '' not in recipients

        # Verify partial log was created
        partial_log = CommunicationLog.objects.filter(
            booking=self.booking,
            email_type='booking_confirmation',
            status='partial',
        ).exists()
        assert partial_log

    @override_settings(
        DISTRIBUTION_LIST=['ops@company.com'],
        AWS_SES_FROM_EMAIL='noreply@logistics.example.com',
        AWS_SES_REGION='ap-south-1',
        AWS_ACCESS_KEY_ID='test-key',
        AWS_SECRET_ACCESS_KEY='test-secret',
    )
    @patch('notifications.services.boto3.client')
    def test_ses_failure_raises_for_retry(self, mock_boto_client):
        """Test that SES failure raises ClientError for task retry."""
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses
        mock_ses.send_email.side_effect = ClientError(
            {'Error': {'Code': 'MessageRejected', 'Message': 'Email rejected'}},
            'SendEmail',
        )

        service = EmailNotificationService()
        with pytest.raises(ClientError):
            service.send_booking_confirmation(self.booking.id)

    @override_settings(
        DISTRIBUTION_LIST=[''],
        AWS_SES_FROM_EMAIL='noreply@logistics.example.com',
        AWS_SES_REGION='ap-south-1',
        AWS_ACCESS_KEY_ID='test-key',
        AWS_SECRET_ACCESS_KEY='test-secret',
    )
    @patch('notifications.services.boto3.client')
    def test_no_recipients_logs_failure(self, mock_boto_client):
        """Test that no recipients at all logs a failure."""
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses

        # Remove client email and have empty distribution list
        self.client_entity.email = ''
        self.client_entity.save()

        service = EmailNotificationService()
        service.send_booking_confirmation(self.booking.id)

        # SES should not be called
        mock_ses.send_email.assert_not_called()

        # Failure log should be created
        log = CommunicationLog.objects.filter(
            booking=self.booking,
            email_type='booking_confirmation',
            status='failed',
        ).last()
        assert log is not None
        assert 'No recipients' in log.error_message


@pytest.mark.django_db
class TestBookingConfirmationCeleryTask(TestCase):
    """Tests for the Celery task retry logic."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testops2', password='testpass123'
        )
        self.client_entity = Client.objects.create(
            name='Task Test Client', email='taskclient@example.com'
        )
        self.shipping_line = ShippingLine.objects.create(
            name='MSC Line', code='MSC'
        )
        self.pol = Port.objects.create(name='Chennai', code='INMAA', country='India')
        self.pod = Port.objects.create(name='Singapore', code='SGSIN', country='Singapore')
        self.commodity = Commodity.objects.create(name='Textiles', hs_code='5209')

        self.booking = Booking.objects.create(
            booking_no='BK-TASK-001',
            booking_date=date.today(),
            booking_validity_date=date.today() + timedelta(days=30),
            forwarding_window_start=date.today(),
            forwarding_window_end=date.today() + timedelta(days=14),
            shipping_line=self.shipping_line,
            pol=self.pol,
            pod=self.pod,
            client=self.client_entity,
            commodity=self.commodity,
            cargo_type=Booking.CargoType.FCL,
            shipment_type='Export',
            stuffing_type='Factory',
            created_by=self.user,
        )

    @override_settings(
        DISTRIBUTION_LIST=['ops@company.com'],
        AWS_SES_FROM_EMAIL='noreply@logistics.example.com',
        AWS_SES_REGION='ap-south-1',
        AWS_ACCESS_KEY_ID='test-key',
        AWS_SECRET_ACCESS_KEY='test-secret',
    )
    @patch('notifications.services.boto3.client')
    def test_task_success(self, mock_boto_client):
        """Test task completes successfully on first attempt."""
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses

        # Call task synchronously
        send_booking_confirmation_task(self.booking.id)

        # Verify email was sent
        mock_ses.send_email.assert_called_once()

        # Verify CommunicationLog created
        log = CommunicationLog.objects.filter(
            booking=self.booking,
            email_type='booking_confirmation',
            status='sent',
        ).exists()
        assert log

    @override_settings(
        DISTRIBUTION_LIST=['ops@company.com'],
        AWS_SES_FROM_EMAIL='noreply@logistics.example.com',
        AWS_SES_REGION='ap-south-1',
        AWS_ACCESS_KEY_ID='test-key',
        AWS_SECRET_ACCESS_KEY='test-secret',
    )
    @patch('notifications.services.boto3.client')
    def test_task_retry_on_ses_failure(self, mock_boto_client):
        """Test that the task retries on SES failure and logs failure after exhaustion."""
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses
        mock_ses.send_email.side_effect = ClientError(
            {'Error': {'Code': 'Throttling', 'Message': 'Rate exceeded'}},
            'SendEmail',
        )

        # Apply the task eagerly - Celery eager mode processes retries immediately
        result = send_booking_confirmation_task.apply(
            args=[self.booking.id],
            throw=False,
        )

        # In eager mode, the task retries all 3 times and then logs failure.
        # The send_email should have been called 4 times total (initial + 3 retries)
        assert mock_ses.send_email.call_count == 4

        # After all retries exhausted, a failure log should exist
        log = CommunicationLog.objects.filter(
            booking=self.booking,
            email_type='booking_confirmation',
            status='failed',
        ).last()
        assert log is not None
        assert 'All retries exhausted' in log.error_message

    @override_settings(
        DISTRIBUTION_LIST=['ops@company.com'],
        AWS_SES_FROM_EMAIL='noreply@logistics.example.com',
        AWS_SES_REGION='ap-south-1',
        AWS_ACCESS_KEY_ID='test-key',
        AWS_SECRET_ACCESS_KEY='test-secret',
    )
    @patch('notifications.services.boto3.client')
    def test_task_logs_failure_after_all_retries(self, mock_boto_client):
        """Test that after all retries, failure is logged in CommunicationLog."""
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses
        mock_ses.send_email.side_effect = ClientError(
            {'Error': {'Code': 'Throttling', 'Message': 'Rate exceeded'}},
            'SendEmail',
        )

        # Use apply() which processes retries eagerly
        send_booking_confirmation_task.apply(
            args=[self.booking.id],
            throw=False,
        )

        # Verify failure logged
        log = CommunicationLog.objects.filter(
            booking=self.booking,
            email_type='booking_confirmation',
            status='failed',
        ).last()
        assert log is not None
        assert 'All retries exhausted' in log.error_message

    def test_task_handles_missing_booking(self):
        """Test task handles non-existent booking gracefully."""
        # Should not raise - just logs error
        send_booking_confirmation_task(99999)

        # No communication log should be created
        assert CommunicationLog.objects.filter(
            booking_id=99999
        ).count() == 0


@pytest.mark.django_db
class TestBookingConfirmationTemplate(TestCase):
    """Tests for the email template rendering."""

    def test_template_renders_with_all_fields(self):
        """Test template renders correctly with all context fields."""
        context = {
            'booking_no': 'BK-TEST-001',
            'customer_name': 'Acme Corp',
            'por': 'Delhi ICD',
            'pol': 'Mumbai',
            'pod': 'Rotterdam',
            'stuffing_point': 'Mumbai CFS',
            'clearance_point': 'Nhava Sheva',
            'container_summary': '2 x 20ft, 1 x 40ft HC',
            'vessel_voyage': 'MSC Oscar / V001',
            'shipping_line': 'Maersk',
            'etd': '15-Jan-2025 10:00',
            'eta': '05-Feb-2025 08:00',
        }

        html = render_to_string('notifications/booking_confirmation.html', context)

        assert 'BK-TEST-001' in html
        assert 'Acme Corp' in html
        assert 'Delhi ICD' in html
        assert 'Mumbai' in html
        assert 'Rotterdam' in html
        assert 'Mumbai CFS' in html
        assert 'Nhava Sheva' in html
        assert '2 x 20ft, 1 x 40ft HC' in html
        assert 'MSC Oscar / V001' in html
        assert 'Maersk' in html
        assert '15-Jan-2025 10:00' in html
        assert '05-Feb-2025 08:00' in html

    def test_template_shows_tbd_for_missing_values(self):
        """Test template correctly displays TBD for missing values."""
        context = {
            'booking_no': 'BK-TEST-002',
            'customer_name': 'Test Customer',
            'por': 'TBD',
            'pol': 'Mumbai',
            'pod': 'Rotterdam',
            'stuffing_point': 'TBD',
            'clearance_point': 'TBD',
            'container_summary': 'TBD',
            'vessel_voyage': 'TBD',
            'shipping_line': 'Maersk',
            'etd': 'TBD',
            'eta': 'TBD',
        }

        html = render_to_string('notifications/booking_confirmation.html', context)

        # Count TBD occurrences - should be present for missing fields
        assert html.count('TBD') >= 5


@pytest.mark.django_db
class TestBookingCreationTriggersEmail(TestCase):
    """Test that booking creation queues the email task."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testops3', password='testpass123'
        )
        self.client_entity = Client.objects.create(
            name='Integration Client', email='integration@example.com'
        )
        self.shipping_line = ShippingLine.objects.create(
            name='Hapag', code='HLCU'
        )
        self.pol = Port.objects.create(name='Kolkata', code='INCCU', country='India')
        self.pod = Port.objects.create(name='Hamburg', code='DEHAM', country='Germany')
        self.commodity = Commodity.objects.create(name='Rice', hs_code='1006')

    @patch('notifications.tasks.send_booking_confirmation_task.delay')
    def test_create_booking_queues_email_task(self, mock_delay):
        """Test that BookingService.create_booking() queues the email task."""
        from bookings.services import BookingService

        data = {
            'booking_no': 'BK-INT-001',
            'booking_date': date.today(),
            'booking_validity_date': date.today() + timedelta(days=30),
            'forwarding_window_start': date.today(),
            'forwarding_window_end': date.today() + timedelta(days=14),
            'shipping_line': self.shipping_line,
            'pol': self.pol,
            'pod': self.pod,
            'client': self.client_entity,
            'commodity': self.commodity,
            'cargo_type': Booking.CargoType.FCL,
            'shipment_type': 'Export',
            'stuffing_type': 'Factory',
        }

        booking = BookingService.create_booking(data, self.user)

        # Verify task was queued with booking ID
        mock_delay.assert_called_once_with(booking.id)
