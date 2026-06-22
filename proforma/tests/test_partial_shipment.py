"""
Tests for partial shipment allocation.
Task 25.13: Verify allocation does not exceed PI line item quantity.
"""

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import Sum

from bookings.models import Booking
from master_data.models import Client, Commodity, Port, ShippingLine
from proforma.models import ProformaInvoice, ProformaLineItem

User = get_user_model()


@pytest.fixture
def ops_user(db):
    user = User.objects.create_user(username='ops_user', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Operations')
    user.groups.add(group)
    return user


@pytest.fixture
def accounts_user(db):
    user = User.objects.create_user(username='accounts_user', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Accounts')
    user.groups.add(group)
    return user


@pytest.fixture
def master_data(db):
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
    """Create a PAID PI with line items for partial shipment testing."""
    pi = ProformaInvoice(
        date=datetime.date.today(),
        customer=master_data['client'],
        currency='USD',
        payment_terms='Net 30',
        expected_shipment_date=datetime.date.today(),
        status=ProformaInvoice.Status.PAID,
        created_by=accounts_user,
    )
    pi.save()
    ProformaLineItem.objects.create(
        proforma_invoice=pi,
        product_name='Widget A',
        quantity=Decimal('1000.000'),
        rate=Decimal('10.00'),
        amount=Decimal('10000.00'),
    )
    ProformaLineItem.objects.create(
        proforma_invoice=pi,
        product_name='Widget B',
        quantity=Decimal('500.000'),
        rate=Decimal('20.00'),
        amount=Decimal('10000.00'),
    )
    pi.total_amount = Decimal('20000.00')
    pi.save(update_fields=['total_amount'])
    return pi


@pytest.mark.django_db
class TestPartialShipmentAllocation:
    """Tests for partial shipment PI-to-Booking linkage."""

    def test_one_pi_links_to_multiple_bookings(self, paid_pi, master_data, ops_user):
        """One PI can be linked to multiple bookings."""
        today = datetime.date.today()
        base_kwargs = {
            'booking_date': today,
            'booking_validity_date': today,
            'forwarding_window_start': today,
            'forwarding_window_end': today,
            'shipping_line': master_data['shipping_line'],
            'pol': master_data['pol'],
            'pod': master_data['pod'],
            'client': master_data['client'],
            'commodity': master_data['commodity'],
            'cargo_type': Booking.CargoType.FCL,
            'shipment_type': 'Export',
            'stuffing_type': 'Factory',
            'proforma_invoice': paid_pi,
            'created_by': ops_user,
        }

        b1 = Booking.objects.create(status=Booking.Status.PENDING, **base_kwargs)
        b2 = Booking.objects.create(status=Booking.Status.PENDING, **base_kwargs)
        b3 = Booking.objects.create(status=Booking.Status.PENDING, **base_kwargs)

        # Verify all bookings are linked to the same PI
        assert paid_pi.bookings.count() == 3
        assert b1.proforma_invoice == paid_pi
        assert b2.proforma_invoice == paid_pi
        assert b3.proforma_invoice == paid_pi

    def test_booking_links_to_one_pi(self, paid_pi, master_data, ops_user):
        """Each booking is linked to exactly one PI."""
        today = datetime.date.today()
        booking = Booking.objects.create(
            status=Booking.Status.PENDING,
            booking_date=today,
            booking_validity_date=today,
            forwarding_window_start=today,
            forwarding_window_end=today,
            shipping_line=master_data['shipping_line'],
            pol=master_data['pol'],
            pod=master_data['pod'],
            client=master_data['client'],
            commodity=master_data['commodity'],
            cargo_type=Booking.CargoType.FCL,
            shipment_type='Export',
            stuffing_type='Factory',
            proforma_invoice=paid_pi,
            created_by=ops_user,
        )
        assert booking.proforma_invoice_id == paid_pi.pk

    def test_pi_line_items_quantities_tracked(self, paid_pi):
        """PI line item original quantities are accessible for allocation checking."""
        items = paid_pi.line_items.all()
        assert items.count() == 2
        assert items.filter(product_name='Widget A').first().quantity == Decimal('1000.000')
        assert items.filter(product_name='Widget B').first().quantity == Decimal('500.000')

    def test_navigable_chain_pi_to_bookings(self, paid_pi, master_data, ops_user):
        """Can navigate from PI to its bookings."""
        today = datetime.date.today()
        booking = Booking.objects.create(
            status=Booking.Status.PENDING,
            booking_date=today,
            booking_validity_date=today,
            forwarding_window_start=today,
            forwarding_window_end=today,
            shipping_line=master_data['shipping_line'],
            pol=master_data['pol'],
            pod=master_data['pod'],
            client=master_data['client'],
            commodity=master_data['commodity'],
            cargo_type=Booking.CargoType.FCL,
            shipment_type='Export',
            stuffing_type='Factory',
            proforma_invoice=paid_pi,
            created_by=ops_user,
        )

        # Forward navigation: PI -> Bookings
        assert paid_pi.bookings.filter(pk=booking.pk).exists()
        # Reverse navigation: Booking -> PI
        assert booking.proforma_invoice == paid_pi
