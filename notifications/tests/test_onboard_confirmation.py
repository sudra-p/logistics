"""
Tests for the onboard confirmation email notification feature.

Covers:
- Email template renders container table correctly
- Blank for unavailable field values
- Missing client email: skip send, log error
- CommunicationLog created on success
- Task triggered on status change to COMPLETED
- Retry logic on SES failure
- BL Number from linked BillOfLading model
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import TestCase, override_settings

from bl.models import BillOfLading
from bookings.models import Booking, CommunicationLog, Container
from master_data.models import (
    Client,
    Commodity,
    Consignee,
    ContainerType,
    Port,
    Shipper,
    ShippingLine,
    Vessel,
)
from notifications.services import EmailNotificationService
from notifications.tasks import send_onboard_confirmation_task

User = get_user_model()


@pytest.mark.django_db
class TestOnboardConfirmationEmail(TestCase):
    """Tests for the onboard confirmation email service."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testops_onboard', password='testpass123'
        )
        self.client_entity = Client.objects.create(
            name='Onboard Client', email='onboard@example.com'
        )
        self.shipping_line = ShippingLine.objects.create(
            name='Maersk OB', code='MAEU'
        )
        self.pol = Port.objects.create(name='Mumbai OB', code='INMUN', country='India')
        self.pod = Port.objects.create(name='Rotterdam OB', code='NLRTM', country='Netherlands')
        self.fpd = Port.objects.create(name='Antwerp', code='BEANR', country='Belgium')
        self.commodity = Commodity.objects.create(name='Electronics OB', hs_code='8471')
        self.vessel = Vessel.objects.create(name='MSC Oscar', imo_number='9703318')
        self.container_type = ContainerType.objects.create(name='Dry OB', code='DRY')

        self.booking = Booking.objects.create(
            booking_no='BK-OB-001',
            booking_date=date.today(),
            booking_validity_date=date.today() + timedelta(days=30),
            forwarding_window_start=date.today(),
            forwarding_window_end=date.today() + timedelta(days=14),
            shipping_line=self.shipping_line,
            pol=self.pol,
            pod=self.pod,
            fpd=self.fpd,
            client=self.client_entity,
            commodity=self.commodity,
            vessel=self.vessel,
            voyage='V100',
            cargo_type=Booking.CargoType.FCL,
            shipment_type='Export',
            stuffing_type='Factory',
            hbl_no='HBL-001',
            created_by=self.user,
        )

        # Add containers
        Container.objects.create(
            booking=self.booking,
            container_type=self.container_type,
            container_size='20FT',
            container_count=1,
            container_no='MSCU1234567',
            seal_no='SEAL001',
        )
        Container.objects.create(
            booking=self.booking,
            container_type=self.container_type,
            container_size='40FT',
            container_count=1,
            container_no='MSCU7654321',
            seal_no='SEAL002',
        )

    @override_settings(
        DISTRIBUTION_LIST=['ops@company.com', 'cs@company.com'],
        AWS_SES_FROM_EMAIL='noreply@logistics.example.com',
        AWS_SES_REGION='ap-south-1',
        AWS_ACCESS_KEY_ID='test-key',
        AWS_SECRET_ACCESS_KEY='test-secret',
    )
    @patch('notifications.services.boto3.client')
    def test_send_onboard_confirmation_success(self, mock_boto_client):
        """Test successful onboard confirmation email sends and logs."""
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses

        service = EmailNotificationService()
        service.send_onboard_confirmation(self.booking.id)

        # Verify SES was called
        mock_ses.send_email.assert_called_once()
        call_kwargs = mock_ses.send_email.call_args[1]

        # Verify recipients include client + distribution list
        recipients = call_kwargs['Destination']['ToAddresses']
        assert 'onboard@example.com' in recipients
        assert 'ops@company.com' in recipients
        assert 'cs@company.com' in recipients

        # Verify subject contains Booking No
        subject = call_kwargs['Message']['Subject']['Data']
        assert 'Onboard Confirmation' in subject
        assert 'BK-OB-001' in subject

        # Verify CommunicationLog created
        log = CommunicationLog.objects.filter(
            booking=self.booking, email_type='onboard_confirmation'
        ).last()
        assert log is not None
        assert log.status == 'sent'
        assert log.sent_at is not None
        assert 'onboard@example.com' in log.recipients

    @override_settings(
        DISTRIBUTION_LIST=['ops@company.com'],
        AWS_SES_FROM_EMAIL='noreply@logistics.example.com',
        AWS_SES_REGION='ap-south-1',
        AWS_ACCESS_KEY_ID='test-key',
        AWS_SECRET_ACCESS_KEY='test-secret',
    )
    @patch('notifications.services.boto3.client')
    def test_template_renders_container_table(self, mock_boto_client):
        """Test that the email template renders a table with container data."""
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses

        service = EmailNotificationService()
        service.send_onboard_confirmation(self.booking.id)

        call_kwargs = mock_ses.send_email.call_args[1]
        html_body = call_kwargs['Message']['Body']['Html']['Data']

        # Verify container details in table
        assert 'BK-OB-001' in html_body  # Booking No
        assert 'MSCU1234567' in html_body  # Container No 1
        assert 'MSCU7654321' in html_body  # Container No 2
        assert '20ft' in html_body  # Container Size
        assert '40ft' in html_body  # Container Size
        assert 'Antwerp' in html_body  # FPD
        assert 'Maersk OB' in html_body  # Shipping Line
        assert 'HBL-001' in html_body  # BL No

    @override_settings(
        DISTRIBUTION_LIST=['ops@company.com'],
        AWS_SES_FROM_EMAIL='noreply@logistics.example.com',
        AWS_SES_REGION='ap-south-1',
        AWS_ACCESS_KEY_ID='test-key',
        AWS_SECRET_ACCESS_KEY='test-secret',
    )
    @patch('notifications.services.boto3.client')
    def test_blank_for_unavailable_field_values(self, mock_boto_client):
        """Test that unavailable field values render as blank in the table."""
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses

        # Create booking without optional fields (no fpd, no hbl_no)
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
        Container.objects.create(
            booking=booking_minimal,
            container_type=self.container_type,
            container_size='20FT',
            container_count=1,
            container_no='',  # No container number
        )

        service = EmailNotificationService()
        service.send_onboard_confirmation(booking_minimal.id)

        call_kwargs = mock_ses.send_email.call_args[1]
        html_body = call_kwargs['Message']['Body']['Html']['Data']

        # Template should render without errors. The fields without data
        # should be blank (empty td cells), not showing 'None' or errors.
        assert 'None' not in html_body

    @override_settings(
        DISTRIBUTION_LIST=['ops@company.com', 'cs@company.com'],
        AWS_SES_FROM_EMAIL='noreply@logistics.example.com',
        AWS_SES_REGION='ap-south-1',
        AWS_ACCESS_KEY_ID='test-key',
        AWS_SECRET_ACCESS_KEY='test-secret',
    )
    @patch('notifications.services.boto3.client')
    def test_missing_client_email_skips_send_logs_error(self, mock_boto_client):
        """Test that missing client email skips send entirely and logs error."""
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses

        # Set client email to empty
        self.client_entity.email = ''
        self.client_entity.save()

        service = EmailNotificationService()
        service.send_onboard_confirmation(self.booking.id)

        # SES should NOT be called (unlike booking confirmation which sends to distro list)
        mock_ses.send_email.assert_not_called()

        # Error log should be created
        log = CommunicationLog.objects.filter(
            booking=self.booking,
            email_type='onboard_confirmation',
            status='failed',
        ).last()
        assert log is not None
        assert 'Client email is missing' in log.error_message

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
            service.send_onboard_confirmation(self.booking.id)


@pytest.mark.django_db
class TestOnboardConfirmationCeleryTask(TestCase):
    """Tests for the onboard confirmation Celery task retry logic."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testops_ob_task', password='testpass123'
        )
        self.client_entity = Client.objects.create(
            name='Task OB Client', email='obtask@example.com'
        )
        self.shipping_line = ShippingLine.objects.create(
            name='MSC OB', code='MSC'
        )
        self.pol = Port.objects.create(name='Chennai OB', code='INMAA', country='India')
        self.pod = Port.objects.create(name='Singapore OB', code='SGSIN', country='Singapore')
        self.commodity = Commodity.objects.create(name='Textiles OB', hs_code='5209')
        self.container_type = ContainerType.objects.create(name='Reefer OB', code='REF')

        self.booking = Booking.objects.create(
            booking_no='BK-OB-TASK-001',
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

        Container.objects.create(
            booking=self.booking,
            container_type=self.container_type,
            container_size='40FT_HC',
            container_count=1,
            container_no='TRIU9876543',
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

        send_onboard_confirmation_task(self.booking.id)

        mock_ses.send_email.assert_called_once()

        log = CommunicationLog.objects.filter(
            booking=self.booking,
            email_type='onboard_confirmation',
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
        """Test that the task retries on SES failure and logs after exhaustion."""
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses
        mock_ses.send_email.side_effect = ClientError(
            {'Error': {'Code': 'Throttling', 'Message': 'Rate exceeded'}},
            'SendEmail',
        )

        result = send_onboard_confirmation_task.apply(
            args=[self.booking.id],
            throw=False,
        )

        # initial + 3 retries = 4 calls
        assert mock_ses.send_email.call_count == 4

        # After all retries, failure log exists
        log = CommunicationLog.objects.filter(
            booking=self.booking,
            email_type='onboard_confirmation',
            status='failed',
        ).last()
        assert log is not None
        assert 'All retries exhausted' in log.error_message

    def test_task_handles_missing_booking(self):
        """Test task handles non-existent booking gracefully."""
        send_onboard_confirmation_task(99999)

        assert CommunicationLog.objects.filter(
            booking_id=99999
        ).count() == 0


@pytest.mark.django_db
class TestOnboardConfirmationTemplate(TestCase):
    """Tests for the onboard confirmation email template rendering."""

    def test_template_renders_container_table(self):
        """Test template renders container rows in a table."""
        context = {
            'booking_no': 'BK-TPL-001',
            'customer_name': 'Acme Corp',
            'vessel_voyage': 'MSC Oscar / V001',
            'container_rows': [
                {
                    'booking_no': 'BK-TPL-001',
                    'container_no': 'MSCU1111111',
                    'container_size': '20ft',
                    'fpd': 'Antwerp',
                    'shipping_line': 'Maersk',
                    'bl_no': 'HBL-100',
                },
                {
                    'booking_no': 'BK-TPL-001',
                    'container_no': 'MSCU2222222',
                    'container_size': '40ft HC',
                    'fpd': 'Hamburg',
                    'shipping_line': 'Maersk',
                    'bl_no': 'HBL-100',
                },
            ],
        }

        html = render_to_string('notifications/onboard_confirmation.html', context)

        assert 'BK-TPL-001' in html
        assert 'MSCU1111111' in html
        assert 'MSCU2222222' in html
        assert '20ft' in html
        assert '40ft HC' in html
        assert 'Antwerp' in html
        assert 'Hamburg' in html
        assert 'Maersk' in html
        assert 'HBL-100' in html
        assert 'MSC Oscar / V001' in html

    def test_template_blank_for_unavailable_values(self):
        """Test template shows blank (empty) for missing container field values."""
        context = {
            'booking_no': 'BK-TPL-002',
            'customer_name': 'Test Corp',
            'vessel_voyage': 'TBD',
            'container_rows': [
                {
                    'booking_no': '',
                    'container_no': '',
                    'container_size': '20ft',
                    'fpd': '',
                    'shipping_line': '',
                    'bl_no': '',
                },
            ],
        }

        html = render_to_string('notifications/onboard_confirmation.html', context)

        # Should not contain None or error text
        assert 'None' not in html
        # Should still render without errors
        assert '20ft' in html


@pytest.mark.django_db
class TestStatusChangeTriggersOnboardEmail(TestCase):
    """Test that status change to COMPLETED triggers onboard confirmation email."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testops_status', password='testpass123'
        )
        self.client_entity = Client.objects.create(
            name='Status Client', email='status@example.com'
        )
        self.shipping_line = ShippingLine.objects.create(
            name='CMA CGM', code='CMDU'
        )
        self.pol = Port.objects.create(name='Mundra', code='INMUN2', country='India')
        self.pod = Port.objects.create(name='Felixstowe', code='GBFXT', country='UK')
        self.commodity = Commodity.objects.create(name='Chemicals', hs_code='2901')

        self.booking = Booking.objects.create(
            booking_no='BK-STATUS-001',
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
            status=Booking.Status.DO_BOOKING_EDIT,
            created_by=self.user,
        )

    @patch('notifications.tasks.send_onboard_confirmation_task.delay')
    def test_status_change_to_completed_triggers_email(self, mock_delay):
        """Test that BookingService.change_status() to COMPLETED queues email task."""
        from bookings.services import BookingService

        BookingService.change_status(
            self.booking.id, Booking.Status.COMPLETED, self.user
        )

        mock_delay.assert_called_once_with(self.booking.id)

    @patch('notifications.tasks.send_onboard_confirmation_task.delay')
    def test_status_change_to_non_completed_does_not_trigger_email(self, mock_delay):
        """Test that transitioning to a non-COMPLETED status does not queue email."""
        from bookings.services import BookingService

        # Set booking back to PENDING for this test
        self.booking.status = Booking.Status.PENDING
        self.booking.save()

        BookingService.change_status(
            self.booking.id, Booking.Status.DO_BOOKING_EDIT, self.user
        )

        mock_delay.assert_not_called()


@pytest.mark.django_db
class TestOnboardConfirmationBLNumber(TestCase):
    """Tests for BL Number sourced from the linked BillOfLading model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testops_bl', password='testpass123'
        )
        self.client_entity = Client.objects.create(
            name='BL Client', email='blclient@example.com'
        )
        self.shipping_line = ShippingLine.objects.create(
            name='Hapag BL', code='HLCU'
        )
        self.pol = Port.objects.create(name='Nhava Sheva BL', code='INNSA', country='India')
        self.pod = Port.objects.create(name='Jebel Ali BL', code='AEJEA', country='UAE')
        self.fpd = Port.objects.create(name='Dammam BL', code='SADMM', country='Saudi Arabia')
        self.commodity = Commodity.objects.create(name='Rice BL', hs_code='1006')
        self.vessel = Vessel.objects.create(name='Hapag Berlin', imo_number='9601234')
        self.container_type = ContainerType.objects.create(name='Dry BL', code='DRYBL')
        self.shipper = Shipper.objects.create(name='BL Shipper')
        self.consignee = Consignee.objects.create(name='BL Consignee')

        self.booking = Booking.objects.create(
            booking_no='BK-BL-001',
            booking_date=date.today(),
            booking_validity_date=date.today() + timedelta(days=30),
            forwarding_window_start=date.today(),
            forwarding_window_end=date.today() + timedelta(days=14),
            shipping_line=self.shipping_line,
            pol=self.pol,
            pod=self.pod,
            fpd=self.fpd,
            client=self.client_entity,
            commodity=self.commodity,
            vessel=self.vessel,
            voyage='V200',
            cargo_type=Booking.CargoType.FCL,
            shipment_type='Export',
            stuffing_type='Factory',
            hbl_no='HBL-FALLBACK',
            created_by=self.user,
        )

        Container.objects.create(
            booking=self.booking,
            container_type=self.container_type,
            container_size='20FT',
            container_count=1,
            container_no='HLCU1234567',
            seal_no='SEAL-BL-001',
        )

    @override_settings(
        DISTRIBUTION_LIST=['ops@company.com'],
        AWS_SES_FROM_EMAIL='noreply@logistics.example.com',
        AWS_SES_REGION='ap-south-1',
        AWS_ACCESS_KEY_ID='test-key',
        AWS_SECRET_ACCESS_KEY='test-secret',
    )
    @patch('notifications.services.boto3.client')
    def test_bl_number_from_linked_bill_of_lading(self, mock_boto_client):
        """Test that BL number is sourced from the linked BillOfLading model."""
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses

        # Create a linked BillOfLading
        BillOfLading.objects.create(
            booking=self.booking,
            bl_number='HLCU-BL-2024-001',
            bl_type=BillOfLading.BLType.LINE,
            container_number='HLCU1234567',
            vessel_name='Hapag Berlin',
            voyage_number='V200',
            shipper=self.shipper,
            consignee=self.consignee,
            created_by=self.user,
        )

        service = EmailNotificationService()
        service.send_onboard_confirmation(self.booking.id)

        call_kwargs = mock_ses.send_email.call_args[1]
        html_body = call_kwargs['Message']['Body']['Html']['Data']

        # BL number from BillOfLading model should be used, NOT hbl_no fallback
        assert 'HLCU-BL-2024-001' in html_body
        assert 'HBL-FALLBACK' not in html_body

    @override_settings(
        DISTRIBUTION_LIST=['ops@company.com'],
        AWS_SES_FROM_EMAIL='noreply@logistics.example.com',
        AWS_SES_REGION='ap-south-1',
        AWS_ACCESS_KEY_ID='test-key',
        AWS_SECRET_ACCESS_KEY='test-secret',
    )
    @patch('notifications.services.boto3.client')
    def test_bl_number_falls_back_to_hbl_no(self, mock_boto_client):
        """Test that BL number falls back to booking.hbl_no when no BillOfLading linked."""
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses

        # No BillOfLading record linked - should use hbl_no fallback
        service = EmailNotificationService()
        service.send_onboard_confirmation(self.booking.id)

        call_kwargs = mock_ses.send_email.call_args[1]
        html_body = call_kwargs['Message']['Body']['Html']['Data']

        # Should use hbl_no as fallback
        assert 'HBL-FALLBACK' in html_body

    @override_settings(
        DISTRIBUTION_LIST=['ops@company.com'],
        AWS_SES_FROM_EMAIL='noreply@logistics.example.com',
        AWS_SES_REGION='ap-south-1',
        AWS_ACCESS_KEY_ID='test-key',
        AWS_SECRET_ACCESS_KEY='test-secret',
    )
    @patch('notifications.services.boto3.client')
    def test_bl_number_falls_back_to_mbl_no(self, mock_boto_client):
        """Test that BL number falls back to booking.mbl_no when no BL and no hbl_no."""
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses

        # Clear hbl_no and set mbl_no
        self.booking.hbl_no = ''
        self.booking.mbl_no = 'MBL-FALLBACK'
        self.booking.save()

        service = EmailNotificationService()
        service.send_onboard_confirmation(self.booking.id)

        call_kwargs = mock_ses.send_email.call_args[1]
        html_body = call_kwargs['Message']['Body']['Html']['Data']

        # Should fall back to mbl_no
        assert 'MBL-FALLBACK' in html_body

    @override_settings(
        DISTRIBUTION_LIST=['ops@company.com'],
        AWS_SES_FROM_EMAIL='noreply@logistics.example.com',
        AWS_SES_REGION='ap-south-1',
        AWS_ACCESS_KEY_ID='test-key',
        AWS_SECRET_ACCESS_KEY='test-secret',
    )
    @patch('notifications.services.boto3.client')
    def test_bl_number_empty_when_no_sources(self, mock_boto_client):
        """Test BL number is empty when no BillOfLading and no booking BL fields."""
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses

        # Clear all BL number sources
        self.booking.hbl_no = ''
        self.booking.mbl_no = ''
        self.booking.save()

        service = EmailNotificationService()
        service.send_onboard_confirmation(self.booking.id)

        call_kwargs = mock_ses.send_email.call_args[1]
        html_body = call_kwargs['Message']['Body']['Html']['Data']

        # Should render without errors - no BL text means empty td cell
        assert 'None' not in html_body
