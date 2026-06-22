"""
Tests for Payment status auto-computation.
Task 25.4: Test partial paid, fully paid transitions.
"""

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from master_data.models import Client
from payments.services import PaymentService
from proforma.models import ProformaInvoice, ProformaLineItem

User = get_user_model()


@pytest.fixture
def accounts_user(db):
    user = User.objects.create_user(username='accounts_user', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Accounts')
    user.groups.add(group)
    return user


@pytest.fixture
def client_obj(db):
    return Client.objects.create(name='Test Client', email='client@test.com')


@pytest.fixture
def approved_pi(accounts_user, client_obj):
    """Create an APPROVED PI with total_amount 1000."""
    pi = ProformaInvoice(
        date=datetime.date.today(),
        customer=client_obj,
        currency='USD',
        payment_terms='Net 30',
        expected_shipment_date=datetime.date.today(),
        status=ProformaInvoice.Status.APPROVED,
        created_by=accounts_user,
    )
    pi.save()
    ProformaLineItem.objects.create(
        proforma_invoice=pi,
        product_name='Widget A',
        quantity=Decimal('100.000'),
        rate=Decimal('10.00'),
        amount=Decimal('1000.00'),
    )
    pi.total_amount = Decimal('1000.00')
    pi.save(update_fields=['total_amount'])
    return pi


@pytest.mark.django_db
class TestPaymentStatusAutoComputation:
    """Tests for automatic PI status transitions based on payments."""

    def test_first_payment_transitions_to_payment_pending(self, approved_pi, accounts_user):
        """First payment on APPROVED PI transitions to PAYMENT_PENDING."""
        data = {
            'proforma_invoice': approved_pi,
            'amount': Decimal('500.00'),
            'payment_mode': 'BANK',
            'payment_date': datetime.date.today(),
        }
        PaymentService.record_payment(data, accounts_user)

        approved_pi.refresh_from_db()
        assert approved_pi.status == ProformaInvoice.Status.PAYMENT_PENDING

    def test_partial_payment_stays_payment_pending(self, approved_pi, accounts_user):
        """Partial payment keeps PI in PAYMENT_PENDING status."""
        data1 = {
            'proforma_invoice': approved_pi,
            'amount': Decimal('300.00'),
            'payment_mode': 'BANK',
            'payment_date': datetime.date.today(),
        }
        PaymentService.record_payment(data1, accounts_user)

        data2 = {
            'proforma_invoice': approved_pi,
            'amount': Decimal('200.00'),
            'payment_mode': 'BANK',
            'payment_date': datetime.date.today(),
        }
        PaymentService.record_payment(data2, accounts_user)

        approved_pi.refresh_from_db()
        assert approved_pi.status == ProformaInvoice.Status.PAYMENT_PENDING

    def test_full_payment_transitions_to_paid(self, approved_pi, accounts_user):
        """Full payment transitions PI to PAID."""
        data = {
            'proforma_invoice': approved_pi,
            'amount': Decimal('1000.00'),
            'payment_mode': 'BANK',
            'payment_date': datetime.date.today(),
        }
        PaymentService.record_payment(data, accounts_user)

        approved_pi.refresh_from_db()
        assert approved_pi.status == ProformaInvoice.Status.PAID

    def test_cumulative_payments_reach_paid(self, approved_pi, accounts_user):
        """Multiple partial payments summing to total transitions to PAID."""
        for amount in [Decimal('300.00'), Decimal('300.00'), Decimal('400.00')]:
            data = {
                'proforma_invoice': approved_pi,
                'amount': amount,
                'payment_mode': 'BANK',
                'payment_date': datetime.date.today(),
            }
            PaymentService.record_payment(data, accounts_user)

        approved_pi.refresh_from_db()
        assert approved_pi.status == ProformaInvoice.Status.PAID
