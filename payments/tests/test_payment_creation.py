"""
Tests for Payment creation with validation.
Task 25.3: Test exceeding balance, negative amounts, valid creation.
"""

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import serializers

from master_data.models import Client
from payments.models import Payment
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
class TestPaymentCreation:
    """Tests for payment recording."""

    def test_valid_payment_created(self, approved_pi, accounts_user):
        """A valid payment is created successfully."""
        data = {
            'proforma_invoice': approved_pi,
            'amount': Decimal('500.00'),
            'payment_mode': 'BANK',
            'payment_date': datetime.date.today(),
        }
        payment = PaymentService.record_payment(data, accounts_user)

        assert payment.pk is not None
        assert payment.amount == Decimal('500.00')
        assert payment.proforma_invoice == approved_pi
        assert payment.created_by == accounts_user

    def test_payment_exceeding_balance_rejected(self, approved_pi, accounts_user):
        """Payment that would exceed PI total is rejected."""
        data = {
            'proforma_invoice': approved_pi,
            'amount': Decimal('1500.00'),
            'payment_mode': 'BANK',
            'payment_date': datetime.date.today(),
        }
        with pytest.raises(serializers.ValidationError) as exc_info:
            PaymentService.record_payment(data, accounts_user)
        assert 'amount' in exc_info.value.detail

    def test_cumulative_payments_exceed_balance_rejected(self, approved_pi, accounts_user):
        """Second payment that would exceed remaining balance is rejected."""
        data1 = {
            'proforma_invoice': approved_pi,
            'amount': Decimal('800.00'),
            'payment_mode': 'BANK',
            'payment_date': datetime.date.today(),
        }
        PaymentService.record_payment(data1, accounts_user)

        data2 = {
            'proforma_invoice': approved_pi,
            'amount': Decimal('300.00'),
            'payment_mode': 'CASH',
            'payment_date': datetime.date.today(),
        }
        with pytest.raises(serializers.ValidationError) as exc_info:
            PaymentService.record_payment(data2, accounts_user)
        assert 'amount' in exc_info.value.detail

    def test_multiple_partial_payments(self, approved_pi, accounts_user):
        """Multiple partial payments can be recorded against one PI."""
        for amount in [Decimal('300.00'), Decimal('300.00'), Decimal('400.00')]:
            data = {
                'proforma_invoice': approved_pi,
                'amount': amount,
                'payment_mode': 'BANK',
                'payment_date': datetime.date.today(),
            }
            PaymentService.record_payment(data, accounts_user)

        assert Payment.objects.filter(proforma_invoice=approved_pi).count() == 3

    def test_exact_balance_payment_accepted(self, approved_pi, accounts_user):
        """Payment equal to remaining balance is accepted."""
        data = {
            'proforma_invoice': approved_pi,
            'amount': Decimal('1000.00'),
            'payment_mode': 'LC',
            'payment_date': datetime.date.today(),
        }
        payment = PaymentService.record_payment(data, accounts_user)
        assert payment.pk is not None
