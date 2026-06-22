"""
Tests for auto_create_booking service function.
"""

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import serializers

from bookings.models import Booking
from master_data.models import Client, Commodity, Port, ShippingLine
from proforma.models import ProformaInvoice, ProformaLineItem
from proforma.services import auto_create_booking

User = get_user_model()


@pytest.fixture
def ops_user(db):
    """Create an Operations group user."""
    user = User.objects.create_user(username='ops_user', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Operations')
    user.groups.add(group)
    return user


@pytest.fixture
def accounts_user(db):
    """Create an Accounts group user."""
    user = User.objects.create_user(username='accounts_user', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Accounts')
    user.groups.add(group)
    return user


@pytest.fixture
def master_data(db):
    """Create required master data for booking creation."""
    shipping_line = ShippingLine.objects.create(name='Maersk', code='MAEU')
    pol = Port.objects.create(name='Mumbai Port', code='INMUN', country='India')
    pod = Port.objects.create(name='Rotterdam Port', code='NLRTM', country='Netherlands')
    client = Client.objects.create(name='Test Client', email='client@test.com')
    commodity = Commodity.objects.create(name='Electronics', hs_code='8542')
    return {
        'shipping_line': shipping_line,
        'pol': pol,
        'pod': pod,
        'client': client,
        'commodity': commodity,
    }


@pytest.fixture
def paid_pi(master_data, accounts_user):
    """Create a ProformaInvoice in PAID status."""
    pi = ProformaInvoice(
        date=datetime.date(2024, 3, 1),
        customer=master_data['client'],
        currency='USD',
        exchange_rate=Decimal('83.5000'),
        payment_terms='Net 30',
        expected_shipment_date=datetime.date(2024, 4, 15),
        status=ProformaInvoice.Status.PAID,
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


@pytest.fixture
def draft_pi(master_data, accounts_user):
    """Create a ProformaInvoice in DRAFT status."""
    pi = ProformaInvoice(
        date=datetime.date(2024, 3, 1),
        customer=master_data['client'],
        currency='USD',
        exchange_rate=Decimal('83.5000'),
        payment_terms='Net 30',
        expected_shipment_date=datetime.date(2024, 4, 15),
        status=ProformaInvoice.Status.DRAFT,
        created_by=accounts_user,
    )
    pi.save()
    ProformaLineItem.objects.create(
        proforma_invoice=pi,
        product_name='Widget B',
        quantity=Decimal('50.000'),
        rate=Decimal('20.00'),
        amount=Decimal('1000.00'),
    )
    pi.total_amount = Decimal('1000.00')
    pi.save(update_fields=['total_amount'])
    return pi


class TestAutoCreateBooking:
    """Tests for the auto_create_booking service function."""

    def test_creates_booking_from_paid_pi(self, paid_pi, ops_user, master_data):
        """auto_create_booking creates a Booking linked to a PAID PI."""
        booking = auto_create_booking(
            paid_pi.id,
            ops_user,
            shipping_line=master_data['shipping_line'],
            pol=master_data['pol'],
            pod=master_data['pod'],
            commodity=master_data['commodity'],
            cargo_type='FCL',
            shipment_type='Export',
            stuffing_type='Factory',
        )

        assert booking.pk is not None
        assert booking.client == paid_pi.customer
        assert booking.proforma_invoice == paid_pi
        assert booking.booking_date == paid_pi.expected_shipment_date
        assert booking.booking_validity_date == paid_pi.expected_shipment_date
        assert booking.forwarding_window_start == paid_pi.expected_shipment_date
        assert booking.forwarding_window_end == paid_pi.expected_shipment_date
        assert booking.status == Booking.Status.PENDING
        assert booking.created_by == ops_user

    def test_links_pi_to_booking(self, paid_pi, ops_user, master_data):
        """The created booking has proforma_invoice FK pointing to the PI."""
        booking = auto_create_booking(
            paid_pi.id,
            ops_user,
            shipping_line=master_data['shipping_line'],
            pol=master_data['pol'],
            pod=master_data['pod'],
            commodity=master_data['commodity'],
            cargo_type='FCL',
            shipment_type='Export',
            stuffing_type='Factory',
        )

        # Verify the FK link from both directions
        assert booking.proforma_invoice_id == paid_pi.id
        assert paid_pi.bookings.filter(pk=booking.pk).exists()

    def test_rejects_non_paid_pi(self, draft_pi, ops_user, master_data):
        """auto_create_booking raises ValidationError if PI is not PAID."""
        with pytest.raises(serializers.ValidationError) as exc_info:
            auto_create_booking(
                draft_pi.id,
                ops_user,
                shipping_line=master_data['shipping_line'],
                pol=master_data['pol'],
                pod=master_data['pod'],
                commodity=master_data['commodity'],
                cargo_type='FCL',
                shipment_type='Export',
                stuffing_type='Factory',
            )

        assert 'detail' in exc_info.value.detail
        assert 'PAID' in str(exc_info.value.detail['detail'])

    def test_rejects_nonexistent_pi(self, ops_user, master_data, db):
        """auto_create_booking raises Http404 for a non-existent PI ID."""
        from django.http import Http404

        with pytest.raises(Http404):
            auto_create_booking(
                99999,
                ops_user,
                shipping_line=master_data['shipping_line'],
                pol=master_data['pol'],
                pod=master_data['pod'],
                commodity=master_data['commodity'],
                cargo_type='FCL',
                shipment_type='Export',
                stuffing_type='Factory',
            )

    def test_booking_data_override(self, paid_pi, ops_user, master_data):
        """Caller-supplied booking_data can override pre-filled defaults."""
        custom_date = datetime.date(2024, 5, 1)
        booking = auto_create_booking(
            paid_pi.id,
            ops_user,
            shipping_line=master_data['shipping_line'],
            pol=master_data['pol'],
            pod=master_data['pod'],
            commodity=master_data['commodity'],
            cargo_type='FCL',
            shipment_type='Export',
            stuffing_type='Factory',
            booking_date=custom_date,
        )

        # booking_date should use the override, not the PI's expected_shipment_date
        assert booking.booking_date == custom_date
        # Other dates still use PI's expected_shipment_date
        assert booking.forwarding_window_start == paid_pi.expected_shipment_date
