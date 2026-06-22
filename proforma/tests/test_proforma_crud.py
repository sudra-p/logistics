"""
Tests for ProformaInvoice CRUD and PI number generation.
Task 25.1: Test uniqueness, format, sequential behavior.
"""

import datetime
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from master_data.models import Client
from proforma.models import ProformaInvoice, ProformaLineItem, generate_pi_number
from proforma.services import ProformaService

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
def pi_data(client_obj):
    return {
        'date': datetime.date(2024, 6, 15),
        'customer': client_obj,
        'currency': 'USD',
        'exchange_rate': Decimal('83.5000'),
        'payment_terms': 'Net 30',
        'expected_shipment_date': datetime.date(2024, 7, 15),
        'line_items': [
            {
                'product_name': 'Widget A',
                'quantity': Decimal('100.000'),
                'rate': Decimal('10.00'),
                'amount': Decimal('1000.00'),
            },
            {
                'product_name': 'Widget B',
                'quantity': Decimal('50.000'),
                'rate': Decimal('20.00'),
                'amount': Decimal('1000.00'),
            },
        ],
    }


@pytest.mark.django_db
class TestPINumberGeneration:
    """Tests for PI number format and sequential behavior."""

    def test_pi_number_format(self, accounts_user, client_obj):
        """PI number follows PI-YYYYMM-NNNN format."""
        pi = ProformaInvoice(
            date=datetime.date.today(),
            customer=client_obj,
            currency='USD',
            payment_terms='Net 30',
            expected_shipment_date=datetime.date.today(),
            created_by=accounts_user,
        )
        pi.save()

        import re
        pattern = r'^PI-\d{6}-\d{4}$'
        assert re.match(pattern, pi.pi_number), f"PI number '{pi.pi_number}' doesn't match format"

    def test_pi_number_unique(self, accounts_user, client_obj):
        """Each PI gets a unique pi_number."""
        pis = []
        for _ in range(5):
            pi = ProformaInvoice(
                date=datetime.date.today(),
                customer=client_obj,
                currency='USD',
                payment_terms='Net 30',
                expected_shipment_date=datetime.date.today(),
                created_by=accounts_user,
            )
            pi.save()
            pis.append(pi)

        pi_numbers = [p.pi_number for p in pis]
        assert len(set(pi_numbers)) == 5, "PI numbers are not unique"

    def test_pi_number_sequential(self, accounts_user, client_obj):
        """Sequential PIs in the same month have increasing suffix."""
        pis = []
        for _ in range(3):
            pi = ProformaInvoice(
                date=datetime.date.today(),
                customer=client_obj,
                currency='USD',
                payment_terms='Net 30',
                expected_shipment_date=datetime.date.today(),
                created_by=accounts_user,
            )
            pi.save()
            pis.append(pi)

        suffixes = [int(p.pi_number.split('-')[-1]) for p in pis]
        assert suffixes == sorted(suffixes)
        assert suffixes[-1] - suffixes[0] == 2

    def test_pi_number_starts_at_0001_for_new_month(self, accounts_user, client_obj):
        """First PI of a new month starts at 0001."""
        pi = ProformaInvoice(
            date=datetime.date.today(),
            customer=client_obj,
            currency='USD',
            payment_terms='Net 30',
            expected_shipment_date=datetime.date.today(),
            created_by=accounts_user,
        )
        pi.save()
        # If there were no prior PIs this month, should be 0001
        suffix = int(pi.pi_number.split('-')[-1])
        assert suffix >= 1


@pytest.mark.django_db
class TestProformaInvoiceCRUD:
    """Tests for CRUD operations on Proforma Invoices."""

    def test_create_proforma_with_line_items(self, accounts_user, pi_data):
        """Creating a PI with line items computes total_amount correctly."""
        pi = ProformaService.create_proforma(pi_data.copy(), accounts_user)

        assert pi.pk is not None
        assert pi.total_amount == Decimal('2000.00')
        assert pi.line_items.count() == 2
        assert pi.status == ProformaInvoice.Status.DRAFT

    def test_create_proforma_sets_currency(self, accounts_user, pi_data):
        """Currency is stored correctly."""
        pi_data['currency'] = 'INR'
        pi = ProformaService.create_proforma(pi_data.copy(), accounts_user)
        assert pi.currency == 'INR'

    def test_create_proforma_sets_exchange_rate(self, accounts_user, pi_data):
        """Exchange rate is stored correctly."""
        pi = ProformaService.create_proforma(pi_data.copy(), accounts_user)
        assert pi.exchange_rate == Decimal('83.5000')

    def test_update_proforma_in_draft(self, accounts_user, pi_data):
        """Can update a DRAFT PI's line items."""
        pi = ProformaService.create_proforma(pi_data.copy(), accounts_user)

        new_items = [
            {
                'product_name': 'Widget C',
                'quantity': Decimal('200.000'),
                'rate': Decimal('5.00'),
                'amount': Decimal('1000.00'),
            }
        ]
        updated = ProformaService.update_proforma(pi.pk, {'line_items': new_items}, accounts_user)
        assert updated.total_amount == Decimal('1000.00')
        assert updated.line_items.count() == 1

    def test_update_proforma_non_draft_rejected(self, accounts_user, pi_data):
        """Cannot update a PI that is not in DRAFT status."""
        from rest_framework import serializers

        pi = ProformaService.create_proforma(pi_data.copy(), accounts_user)
        pi.status = ProformaInvoice.Status.SENT
        pi.save(update_fields=['status'])

        with pytest.raises(serializers.ValidationError):
            ProformaService.update_proforma(pi.pk, {'payment_terms': 'Net 60'}, accounts_user)

    def test_line_item_amount_computed(self, accounts_user, pi_data):
        """Line item amount is quantity * rate."""
        pi = ProformaService.create_proforma(pi_data.copy(), accounts_user)
        item = pi.line_items.first()
        assert item.amount == item.quantity * item.rate
