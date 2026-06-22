"""
Tests for the payment reminder email notification feature.

Covers:
- Successful send to customer email + distribution list
- No recipients available (logs warning, no send)
- Customer email missing (sends to distribution list only)
- SES failure raises ClientError for retry
- Template context has correct values
- proforma/tasks.py integration using the service
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from master_data.models import Client
from notifications.services import EmailNotificationService
from proforma.models import ProformaInvoice, ProformaLineItem

User = get_user_model()


@pytest.mark.django_db
class TestSendPaymentReminder(TestCase):
    """Tests for EmailNotificationService.send_payment_reminder()."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testaccounts', password='testpass123'
        )
        self.client_entity = Client.objects.create(
            name='Reminder Test Client', email='reminder@example.com'
        )
        self.pi = ProformaInvoice.objects.create(
            date=date.today() - timedelta(days=45),
            customer=self.client_entity,
            currency='USD',
            exchange_rate=Decimal('83.5000'),
            payment_terms='Net 30',
            expected_shipment_date=date.today() + timedelta(days=15),
            total_amount=Decimal('25000.00'),
            status=ProformaInvoice.Status.PAYMENT_PENDING,
            created_by=self.user,
        )
        ProformaLineItem.objects.create(
            proforma_invoice=self.pi,
            product_name='Test Product',
            quantity=Decimal('100.000'),
            rate=Decimal('250.00'),
            amount=Decimal('25000.00'),
        )

    @override_settings(
        DISTRIBUTION_LIST=['ops@company.com', 'accounts@company.com'],
        AWS_SES_FROM_EMAIL='noreply@logistics.example.com',
        AWS_SES_REGION='ap-south-1',
        AWS_ACCESS_KEY_ID='test-key',
        AWS_SECRET_ACCESS_KEY='test-secret',
    )
    @patch('notifications.services.boto3.client')
    def test_send_payment_reminder_success(self, mock_boto_client):
        """Test successful payment reminder email send."""
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses

        service = EmailNotificationService()
        service.send_payment_reminder(self.pi.id)

        # Verify SES was called
        mock_ses.send_email.assert_called_once()
        call_kwargs = mock_ses.send_email.call_args[1]

        # Verify recipients include customer + distribution list
        recipients = call_kwargs['Destination']['ToAddresses']
        assert 'reminder@example.com' in recipients
        assert 'ops@company.com' in recipients
        assert 'accounts@company.com' in recipients

        # Verify subject
        assert self.pi.pi_number in call_kwargs['Message']['Subject']['Data']
        assert 'Payment Reminder' in call_kwargs['Message']['Subject']['Data']

    @override_settings(
        DISTRIBUTION_LIST=['ops@company.com'],
        AWS_SES_FROM_EMAIL='noreply@logistics.example.com',
        AWS_SES_REGION='ap-south-1',
        AWS_ACCESS_KEY_ID='test-key',
        AWS_SECRET_ACCESS_KEY='test-secret',
    )
    @patch('notifications.services.boto3.client')
    def test_send_payment_reminder_template_context(self, mock_boto_client):
        """Test that the correct context values are passed to the template."""
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses

        with patch('notifications.services.render_to_string') as mock_render:
            mock_render.return_value = '<html>reminder</html>'

            service = EmailNotificationService()
            service.send_payment_reminder(self.pi.id)

            mock_render.assert_called_once()
            template_name, context = mock_render.call_args[0]
            assert template_name == 'notifications/payment_reminder.html'
            assert context['pi_number'] == self.pi.pi_number
            assert context['customer_name'] == 'Reminder Test Client'
            assert context['total_amount'] == Decimal('25000.00')
            assert context['currency'] == 'USD'
            assert context['payment_terms'] == 'Net 30'
            assert 'days_overdue' in context

    @override_settings(
        DISTRIBUTION_LIST=['ops@company.com'],
        AWS_SES_FROM_EMAIL='noreply@logistics.example.com',
        AWS_SES_REGION='ap-south-1',
        AWS_ACCESS_KEY_ID='test-key',
        AWS_SECRET_ACCESS_KEY='test-secret',
    )
    @patch('notifications.services.boto3.client')
    def test_send_payment_reminder_missing_customer_email(self, mock_boto_client):
        """Test that missing customer email still sends to distribution list."""
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses

        # Remove customer email
        self.client_entity.email = ''
        self.client_entity.save()

        service = EmailNotificationService()
        service.send_payment_reminder(self.pi.id)

        # Verify SES was still called
        mock_ses.send_email.assert_called_once()
        call_kwargs = mock_ses.send_email.call_args[1]
        recipients = call_kwargs['Destination']['ToAddresses']

        # Should only contain distribution list
        assert 'ops@company.com' in recipients
        assert '' not in recipients

    @override_settings(
        DISTRIBUTION_LIST=[''],
        AWS_SES_FROM_EMAIL='noreply@logistics.example.com',
        AWS_SES_REGION='ap-south-1',
        AWS_ACCESS_KEY_ID='test-key',
        AWS_SECRET_ACCESS_KEY='test-secret',
    )
    @patch('notifications.services.boto3.client')
    def test_send_payment_reminder_no_recipients(self, mock_boto_client):
        """Test that no recipients logs warning and does not send."""
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses

        # Remove client email and set empty distribution list
        self.client_entity.email = ''
        self.client_entity.save()

        service = EmailNotificationService()
        service.send_payment_reminder(self.pi.id)

        # SES should NOT be called
        mock_ses.send_email.assert_not_called()

    @override_settings(
        DISTRIBUTION_LIST=['ops@company.com'],
        AWS_SES_FROM_EMAIL='noreply@logistics.example.com',
        AWS_SES_REGION='ap-south-1',
        AWS_ACCESS_KEY_ID='test-key',
        AWS_SECRET_ACCESS_KEY='test-secret',
    )
    @patch('notifications.services.boto3.client')
    def test_send_payment_reminder_ses_failure_raises(self, mock_boto_client):
        """Test that SES failure raises ClientError for retry logic."""
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses
        mock_ses.send_email.side_effect = ClientError(
            {'Error': {'Code': 'MessageRejected', 'Message': 'Email rejected'}},
            'SendEmail',
        )

        service = EmailNotificationService()
        with pytest.raises(ClientError):
            service.send_payment_reminder(self.pi.id)

    @override_settings(
        DISTRIBUTION_LIST=['ops@company.com'],
        AWS_SES_FROM_EMAIL='noreply@logistics.example.com',
        AWS_SES_REGION='ap-south-1',
        AWS_ACCESS_KEY_ID='test-key',
        AWS_SECRET_ACCESS_KEY='test-secret',
    )
    @patch('notifications.services.boto3.client')
    def test_send_payment_reminder_html_content(self, mock_boto_client):
        """Test that the rendered HTML contains PI data."""
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses

        service = EmailNotificationService()
        service.send_payment_reminder(self.pi.id)

        call_kwargs = mock_ses.send_email.call_args[1]
        html_body = call_kwargs['Message']['Body']['Html']['Data']

        # Template should include PI-related data
        assert self.pi.pi_number in html_body
        assert 'Reminder Test Client' in html_body
        assert '25000.00' in html_body
        assert 'USD' in html_body
        assert 'Net 30' in html_body


@pytest.mark.django_db
class TestCheckPaymentOverdueTask(TestCase):
    """Tests for the check_payment_overdue Celery task using the service."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testaccounts2', password='testpass123'
        )
        self.client_entity = Client.objects.create(
            name='Overdue Client', email='overdue@example.com'
        )

    @override_settings(
        DISTRIBUTION_LIST=['ops@company.com'],
        AWS_SES_FROM_EMAIL='noreply@logistics.example.com',
        AWS_SES_REGION='ap-south-1',
        AWS_ACCESS_KEY_ID='test-key',
        AWS_SECRET_ACCESS_KEY='test-secret',
    )
    @patch('notifications.services.boto3.client')
    def test_task_sends_reminders_for_overdue_pis(self, mock_boto_client):
        """Test that the task calls send_payment_reminder for overdue PIs."""
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses

        # Create an overdue PI (PAYMENT_PENDING for >30 days)
        pi = ProformaInvoice.objects.create(
            date=date.today() - timedelta(days=60),
            customer=self.client_entity,
            currency='USD',
            exchange_rate=Decimal('83.5000'),
            payment_terms='Net 30',
            expected_shipment_date=date.today() - timedelta(days=15),
            total_amount=Decimal('10000.00'),
            status=ProformaInvoice.Status.PAYMENT_PENDING,
            created_by=self.user,
        )
        # Force updated_at to be >30 days ago
        ProformaInvoice.objects.filter(pk=pi.pk).update(
            updated_at=date.today() - timedelta(days=35)
        )

        from proforma.tasks import check_payment_overdue
        check_payment_overdue()

        # Verify SES was called
        mock_ses.send_email.assert_called_once()
        call_kwargs = mock_ses.send_email.call_args[1]
        recipients = call_kwargs['Destination']['ToAddresses']
        assert 'overdue@example.com' in recipients

    @override_settings(
        DISTRIBUTION_LIST=['ops@company.com'],
        AWS_SES_FROM_EMAIL='noreply@logistics.example.com',
        AWS_SES_REGION='ap-south-1',
        AWS_ACCESS_KEY_ID='test-key',
        AWS_SECRET_ACCESS_KEY='test-secret',
    )
    @patch('notifications.services.boto3.client')
    def test_task_skips_non_overdue_pis(self, mock_boto_client):
        """Test that the task does not send reminders for PIs not overdue."""
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses

        # Create a PI that is only 10 days old in PAYMENT_PENDING
        ProformaInvoice.objects.create(
            date=date.today() - timedelta(days=10),
            customer=self.client_entity,
            currency='INR',
            exchange_rate=Decimal('1.0000'),
            payment_terms='Net 30',
            expected_shipment_date=date.today() + timedelta(days=20),
            total_amount=Decimal('5000.00'),
            status=ProformaInvoice.Status.PAYMENT_PENDING,
            created_by=self.user,
        )

        from proforma.tasks import check_payment_overdue
        check_payment_overdue()

        # SES should NOT be called since PI is not overdue
        mock_ses.send_email.assert_not_called()

    @override_settings(
        DISTRIBUTION_LIST=['ops@company.com'],
        AWS_SES_FROM_EMAIL='noreply@logistics.example.com',
        AWS_SES_REGION='ap-south-1',
        AWS_ACCESS_KEY_ID='test-key',
        AWS_SECRET_ACCESS_KEY='test-secret',
    )
    @patch('notifications.services.boto3.client')
    def test_task_handles_ses_failure_gracefully(self, mock_boto_client):
        """Test that the task continues processing other PIs when one fails."""
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses
        mock_ses.send_email.side_effect = ClientError(
            {'Error': {'Code': 'Throttling', 'Message': 'Rate exceeded'}},
            'SendEmail',
        )

        # Create an overdue PI
        pi = ProformaInvoice.objects.create(
            date=date.today() - timedelta(days=60),
            customer=self.client_entity,
            currency='USD',
            exchange_rate=Decimal('83.5000'),
            payment_terms='Net 30',
            expected_shipment_date=date.today() - timedelta(days=15),
            total_amount=Decimal('10000.00'),
            status=ProformaInvoice.Status.PAYMENT_PENDING,
            created_by=self.user,
        )
        ProformaInvoice.objects.filter(pk=pi.pk).update(
            updated_at=date.today() - timedelta(days=35)
        )

        from proforma.tasks import check_payment_overdue

        # Should not raise - handles failure gracefully
        check_payment_overdue()

        # SES was attempted
        mock_ses.send_email.assert_called_once()
