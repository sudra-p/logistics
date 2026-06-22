"""
Tests for the check_payment_overdue Celery task.
"""

import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone

from proforma.models import ProformaInvoice, ProformaLineItem
from master_data.models import Client

User = get_user_model()


@pytest.fixture
def accounts_user(db):
    """Create an Accounts group user."""
    user = User.objects.create_user(username='accounts_user', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Accounts')
    user.groups.add(group)
    return user


@pytest.fixture
def client_with_email(db):
    """Create a client with email."""
    return Client.objects.create(name='Test Client', email='client@example.com')


@pytest.fixture
def client_without_email(db):
    """Create a client without email."""
    return Client.objects.create(name='No Email Client', email='')


def create_pi(customer, user, status, days_ago_updated):
    """Helper to create a PI and manually set its updated_at."""
    pi = ProformaInvoice(
        date=datetime.date(2024, 1, 1),
        customer=customer,
        currency='USD',
        exchange_rate=Decimal('83.5000'),
        payment_terms='Net 30',
        expected_shipment_date=datetime.date(2024, 3, 1),
        status=status,
        created_by=user,
    )
    pi.save()
    ProformaLineItem.objects.create(
        proforma_invoice=pi,
        product_name='Widget',
        quantity=Decimal('10.000'),
        rate=Decimal('100.00'),
        amount=Decimal('1000.00'),
    )
    pi.total_amount = Decimal('1000.00')
    pi.save(update_fields=['total_amount'])

    # Manually set updated_at to simulate the PI being in this status for X days
    target_date = timezone.now() - datetime.timedelta(days=days_ago_updated)
    ProformaInvoice.objects.filter(pk=pi.pk).update(updated_at=target_date)
    pi.refresh_from_db()
    return pi


@pytest.mark.django_db
class TestCheckPaymentOverdue:
    """Tests for the check_payment_overdue Celery task."""

    @patch('proforma.tasks.boto3.client')
    def test_sends_reminder_for_overdue_pi(self, mock_boto_client, client_with_email, accounts_user, settings):
        """Task sends email for PI in PAYMENT_PENDING > 30 days."""
        settings.DISTRIBUTION_LIST = ['ops@example.com']
        settings.AWS_SES_REGION = 'us-east-1'
        settings.AWS_SES_FROM_EMAIL = 'noreply@test.com'
        settings.AWS_ACCESS_KEY_ID = 'test-key'
        settings.AWS_SECRET_ACCESS_KEY = 'test-secret'

        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses

        # PI in PAYMENT_PENDING for 35 days (overdue)
        create_pi(client_with_email, accounts_user, ProformaInvoice.Status.PAYMENT_PENDING, 35)

        from proforma.tasks import check_payment_overdue
        check_payment_overdue()

        # Should have sent one email
        mock_ses.send_email.assert_called_once()
        call_kwargs = mock_ses.send_email.call_args[1]
        assert call_kwargs['Source'] == 'noreply@test.com'
        assert 'client@example.com' in call_kwargs['Destination']['ToAddresses']
        assert 'ops@example.com' in call_kwargs['Destination']['ToAddresses']
        assert 'Payment Reminder' in call_kwargs['Message']['Subject']['Data']

    @patch('proforma.tasks.boto3.client')
    def test_does_not_send_for_recent_pi(self, mock_boto_client, client_with_email, accounts_user, settings):
        """Task does not send email for PI in PAYMENT_PENDING < 30 days."""
        settings.DISTRIBUTION_LIST = ['ops@example.com']
        settings.AWS_SES_REGION = 'us-east-1'
        settings.AWS_SES_FROM_EMAIL = 'noreply@test.com'
        settings.AWS_ACCESS_KEY_ID = 'test-key'
        settings.AWS_SECRET_ACCESS_KEY = 'test-secret'

        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses

        # PI in PAYMENT_PENDING for only 10 days (not overdue)
        create_pi(client_with_email, accounts_user, ProformaInvoice.Status.PAYMENT_PENDING, 10)

        from proforma.tasks import check_payment_overdue
        check_payment_overdue()

        mock_ses.send_email.assert_not_called()

    @patch('proforma.tasks.boto3.client')
    def test_does_not_send_for_non_payment_pending_status(self, mock_boto_client, client_with_email, accounts_user, settings):
        """Task only targets PIs with PAYMENT_PENDING status."""
        settings.DISTRIBUTION_LIST = ['ops@example.com']
        settings.AWS_SES_REGION = 'us-east-1'
        settings.AWS_SES_FROM_EMAIL = 'noreply@test.com'
        settings.AWS_ACCESS_KEY_ID = 'test-key'
        settings.AWS_SECRET_ACCESS_KEY = 'test-secret'

        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses

        # PI in DRAFT status for 35 days — should be ignored
        create_pi(client_with_email, accounts_user, ProformaInvoice.Status.DRAFT, 35)
        # PI in PAID status for 35 days — should be ignored
        create_pi(client_with_email, accounts_user, ProformaInvoice.Status.PAID, 35)

        from proforma.tasks import check_payment_overdue
        check_payment_overdue()

        mock_ses.send_email.assert_not_called()

    @patch('proforma.tasks.boto3.client')
    def test_sends_to_distribution_list_when_no_client_email(self, mock_boto_client, client_without_email, accounts_user, settings):
        """Task sends to distribution list even if customer has no email."""
        settings.DISTRIBUTION_LIST = ['ops@example.com', 'admin@example.com']
        settings.AWS_SES_REGION = 'us-east-1'
        settings.AWS_SES_FROM_EMAIL = 'noreply@test.com'
        settings.AWS_ACCESS_KEY_ID = 'test-key'
        settings.AWS_SECRET_ACCESS_KEY = 'test-secret'

        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses

        create_pi(client_without_email, accounts_user, ProformaInvoice.Status.PAYMENT_PENDING, 35)

        from proforma.tasks import check_payment_overdue
        check_payment_overdue()

        mock_ses.send_email.assert_called_once()
        call_kwargs = mock_ses.send_email.call_args[1]
        assert call_kwargs['Destination']['ToAddresses'] == ['ops@example.com', 'admin@example.com']

    @patch('proforma.tasks.boto3.client')
    def test_handles_multiple_overdue_pis(self, mock_boto_client, client_with_email, accounts_user, settings):
        """Task sends emails for all overdue PIs."""
        settings.DISTRIBUTION_LIST = ['ops@example.com']
        settings.AWS_SES_REGION = 'us-east-1'
        settings.AWS_SES_FROM_EMAIL = 'noreply@test.com'
        settings.AWS_ACCESS_KEY_ID = 'test-key'
        settings.AWS_SECRET_ACCESS_KEY = 'test-secret'

        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses

        # Create 3 overdue PIs
        create_pi(client_with_email, accounts_user, ProformaInvoice.Status.PAYMENT_PENDING, 31)
        create_pi(client_with_email, accounts_user, ProformaInvoice.Status.PAYMENT_PENDING, 45)
        create_pi(client_with_email, accounts_user, ProformaInvoice.Status.PAYMENT_PENDING, 60)

        from proforma.tasks import check_payment_overdue
        check_payment_overdue()

        assert mock_ses.send_email.call_count == 3

    @patch('proforma.tasks.boto3.client')
    def test_skips_pi_with_no_recipients(self, mock_boto_client, client_without_email, accounts_user, settings):
        """Task skips sending when no recipients are available at all."""
        settings.DISTRIBUTION_LIST = ['']  # Empty distribution list
        settings.AWS_SES_REGION = 'us-east-1'
        settings.AWS_SES_FROM_EMAIL = 'noreply@test.com'
        settings.AWS_ACCESS_KEY_ID = 'test-key'
        settings.AWS_SECRET_ACCESS_KEY = 'test-secret'

        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses

        # Client has no email and distribution list is empty
        create_pi(client_without_email, accounts_user, ProformaInvoice.Status.PAYMENT_PENDING, 35)

        from proforma.tasks import check_payment_overdue
        check_payment_overdue()

        mock_ses.send_email.assert_not_called()

    @patch('proforma.tasks.boto3.client')
    def test_boundary_exactly_30_days(self, mock_boto_client, client_with_email, accounts_user, settings):
        """Task includes PI that is exactly at the 30-day boundary."""
        settings.DISTRIBUTION_LIST = ['ops@example.com']
        settings.AWS_SES_REGION = 'us-east-1'
        settings.AWS_SES_FROM_EMAIL = 'noreply@test.com'
        settings.AWS_ACCESS_KEY_ID = 'test-key'
        settings.AWS_SECRET_ACCESS_KEY = 'test-secret'

        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses

        # PI updated exactly 30 days ago (on the boundary - should be included due to __lte)
        create_pi(client_with_email, accounts_user, ProformaInvoice.Status.PAYMENT_PENDING, 30)

        from proforma.tasks import check_payment_overdue
        check_payment_overdue()

        # At exactly 30 days the updated_at should be <= threshold, so email is sent
        mock_ses.send_email.assert_called_once()
