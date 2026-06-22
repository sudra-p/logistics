"""
Tests for Packing List creation, finalization, versioning.
Task 25.8.
"""

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.exceptions import ValidationError

from bookings.models import Booking
from invoices.models import PackingList, PackingListLineItem
from invoices.services import PackingListService
from master_data.models import Client, Commodity, Port, ShippingLine
from proforma.models import ProformaInvoice, ProformaLineItem

User = get_user_model()


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
def booking_with_pi(master_data, accounts_user):
    """Create a booking linked to a PI with line items."""
    today = datetime.date.today()
    pi = ProformaInvoice(
        date=today,
        customer=master_data['client'],
        currency='USD',
        payment_terms='Net 30',
        expected_shipment_date=today,
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

    booking = Booking.objects.create(
        status=Booking.Status.BOOKED,
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
        proforma_invoice=pi,
        created_by=accounts_user,
    )
    return booking, pi


@pytest.mark.django_db
class TestPackingListCreation:
    """Tests for Packing List creation."""

    def test_auto_fill_from_pi(self, booking_with_pi, accounts_user):
        """Packing list auto-fills product details from linked PI."""
        booking, pi = booking_with_pi
        pl = PackingListService.create_packing_list(booking.pk, accounts_user)

        assert pl.pk is not None
        assert pl.status == PackingList.Status.DRAFT
        assert pl.line_items.count() == 1
        item = pl.line_items.first()
        assert item.product_name == 'Widget A'
        assert item.quantity == Decimal('100.000')

    def test_create_with_explicit_items(self, booking_with_pi, accounts_user):
        """Can create packing list with explicit items."""
        booking, _ = booking_with_pi
        line_items = [
            {
                'product_name': 'Custom',
                'quantity': Decimal('50.000'),
                'num_packages': 5,
                'net_weight': Decimal('100.000'),
                'gross_weight': Decimal('120.000'),
                'package_type': 'Carton',
            }
        ]
        pl = PackingListService.create_packing_list(booking.pk, accounts_user, line_items=line_items)
        assert pl.line_items.count() == 1
        assert pl.line_items.first().package_type == 'Carton'

    def test_packing_list_number_generated(self, booking_with_pi, accounts_user):
        """Packing list number is auto-generated in PL-YYYYMM-NNNN format."""
        booking, _ = booking_with_pi
        pl = PackingListService.create_packing_list(booking.pk, accounts_user)
        assert pl.packing_list_number.startswith('PL-')


@pytest.mark.django_db
class TestPackingListFinalization:
    """Tests for Packing List finalization."""

    def test_finalize_draft(self, booking_with_pi, accounts_user):
        """Can finalize a DRAFT packing list."""
        booking, _ = booking_with_pi
        pl = PackingListService.create_packing_list(booking.pk, accounts_user)
        finalized = PackingListService.finalize_packing_list(pl.pk, accounts_user)
        assert finalized.status == PackingList.Status.FINALIZED

    def test_finalize_already_finalized_rejected(self, booking_with_pi, accounts_user):
        """Cannot finalize an already-finalized packing list."""
        booking, _ = booking_with_pi
        pl = PackingListService.create_packing_list(booking.pk, accounts_user)
        PackingListService.finalize_packing_list(pl.pk, accounts_user)

        with pytest.raises(ValidationError):
            PackingListService.finalize_packing_list(pl.pk, accounts_user)

    def test_cannot_edit_finalized(self, booking_with_pi, accounts_user):
        """Cannot update a finalized packing list."""
        booking, _ = booking_with_pi
        pl = PackingListService.create_packing_list(booking.pk, accounts_user)
        PackingListService.finalize_packing_list(pl.pk, accounts_user)

        with pytest.raises(ValidationError):
            PackingListService.update_packing_list(pl.pk, accounts_user, line_items=[])


@pytest.mark.django_db
class TestPackingListVersioning:
    """Tests for Packing List versioning."""

    def test_revision_increments(self, booking_with_pi, accounts_user):
        """Creating a revision increments the revision number."""
        booking, _ = booking_with_pi
        pl = PackingListService.create_packing_list(booking.pk, accounts_user)
        assert pl.revision == 1

        PackingListService.finalize_packing_list(pl.pk, accounts_user)
        new_pl = PackingListService.create_revision(pl.pk, accounts_user)
        assert new_pl.revision == 2
        assert new_pl.status == PackingList.Status.DRAFT

    def test_revision_copies_line_items(self, booking_with_pi, accounts_user):
        """New revision copies line items from the previous revision."""
        booking, _ = booking_with_pi
        line_items = [
            {
                'product_name': 'Widget A',
                'quantity': Decimal('100.000'),
                'num_packages': 10,
                'net_weight': Decimal('500.000'),
                'gross_weight': Decimal('600.000'),
                'package_type': 'Pallet',
            }
        ]
        pl = PackingListService.create_packing_list(booking.pk, accounts_user, line_items=line_items)
        PackingListService.finalize_packing_list(pl.pk, accounts_user)

        new_pl = PackingListService.create_revision(pl.pk, accounts_user)
        assert new_pl.line_items.count() == 1
        item = new_pl.line_items.first()
        assert item.product_name == 'Widget A'
        assert item.package_type == 'Pallet'

    def test_cannot_revise_non_finalized(self, booking_with_pi, accounts_user):
        """Cannot create revision of a non-finalized packing list."""
        booking, _ = booking_with_pi
        pl = PackingListService.create_packing_list(booking.pk, accounts_user)

        with pytest.raises(ValidationError):
            PackingListService.create_revision(pl.pk, accounts_user)
