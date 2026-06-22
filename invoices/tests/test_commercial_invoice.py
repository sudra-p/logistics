"""
Tests for Commercial Invoice creation with auto-fill from PI, finalization, versioning.
Task 25.7.
"""

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.exceptions import ValidationError

from bookings.models import Booking
from invoices.models import CommercialInvoice, CommercialInvoiceLineItem
from invoices.services import CommercialInvoiceService
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
    ProformaLineItem.objects.create(
        proforma_invoice=pi,
        product_name='Widget B',
        quantity=Decimal('50.000'),
        rate=Decimal('20.00'),
        amount=Decimal('1000.00'),
    )
    pi.total_amount = Decimal('2000.00')
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
class TestCommercialInvoiceCreation:
    """Tests for Commercial Invoice creation and auto-fill."""

    def test_auto_fill_from_pi(self, booking_with_pi, accounts_user):
        """Invoice auto-fills line items from the linked PI."""
        booking, pi = booking_with_pi
        invoice = CommercialInvoiceService.create_commercial_invoice(booking.pk, accounts_user)

        assert invoice.pk is not None
        assert invoice.status == CommercialInvoice.Status.DRAFT
        assert invoice.line_items.count() == 2

        items = list(invoice.line_items.order_by('pk'))
        assert items[0].product_name == 'Widget A'
        assert items[0].quantity == Decimal('100.000')
        assert items[0].rate == Decimal('10.00')
        assert items[0].amount == Decimal('1000.00')

    def test_create_with_explicit_line_items(self, booking_with_pi, accounts_user):
        """Invoice can be created with explicitly provided line items."""
        booking, _ = booking_with_pi
        line_items = [
            {
                'product_name': 'Custom Product',
                'quantity': Decimal('25.000'),
                'rate': Decimal('40.00'),
                'amount': Decimal('1000.00'),
            }
        ]
        invoice = CommercialInvoiceService.create_commercial_invoice(
            booking.pk, accounts_user, line_items=line_items
        )
        assert invoice.line_items.count() == 1
        assert invoice.line_items.first().product_name == 'Custom Product'

    def test_invoice_number_generated(self, booking_with_pi, accounts_user):
        """Invoice number is auto-generated."""
        booking, _ = booking_with_pi
        invoice = CommercialInvoiceService.create_commercial_invoice(booking.pk, accounts_user)
        assert invoice.invoice_number != ''
        assert invoice.invoice_number.startswith('INV-')


@pytest.mark.django_db
class TestCommercialInvoiceFinalization:
    """Tests for Commercial Invoice finalization."""

    def test_finalize_draft_invoice(self, booking_with_pi, accounts_user):
        """Can finalize a DRAFT invoice."""
        booking, _ = booking_with_pi
        invoice = CommercialInvoiceService.create_commercial_invoice(booking.pk, accounts_user)
        finalized = CommercialInvoiceService.finalize_invoice(invoice.pk, accounts_user)
        assert finalized.status == CommercialInvoice.Status.FINALIZED

    def test_finalize_already_finalized_rejected(self, booking_with_pi, accounts_user):
        """Cannot finalize an already-finalized invoice."""
        booking, _ = booking_with_pi
        invoice = CommercialInvoiceService.create_commercial_invoice(booking.pk, accounts_user)
        CommercialInvoiceService.finalize_invoice(invoice.pk, accounts_user)

        with pytest.raises(ValidationError):
            CommercialInvoiceService.finalize_invoice(invoice.pk, accounts_user)

    def test_cannot_edit_finalized_invoice(self, booking_with_pi, accounts_user):
        """Cannot update a finalized invoice."""
        booking, _ = booking_with_pi
        invoice = CommercialInvoiceService.create_commercial_invoice(booking.pk, accounts_user)
        CommercialInvoiceService.finalize_invoice(invoice.pk, accounts_user)

        with pytest.raises(ValidationError):
            CommercialInvoiceService.update_invoice(invoice.pk, accounts_user, line_items=[])


@pytest.mark.django_db
class TestCommercialInvoiceVersioning:
    """Tests for Commercial Invoice versioning."""

    def test_revision_increments(self, booking_with_pi, accounts_user):
        """Creating a revision increments the revision number."""
        booking, _ = booking_with_pi
        invoice = CommercialInvoiceService.create_commercial_invoice(booking.pk, accounts_user)
        assert invoice.revision == 1

        CommercialInvoiceService.finalize_invoice(invoice.pk, accounts_user)
        new_invoice = CommercialInvoiceService.create_revision(invoice.pk, accounts_user)
        assert new_invoice.revision == 2
        assert new_invoice.status == CommercialInvoice.Status.DRAFT

    def test_revision_copies_line_items(self, booking_with_pi, accounts_user):
        """New revision copies line items from the previous revision."""
        booking, _ = booking_with_pi
        invoice = CommercialInvoiceService.create_commercial_invoice(booking.pk, accounts_user)
        CommercialInvoiceService.finalize_invoice(invoice.pk, accounts_user)

        new_invoice = CommercialInvoiceService.create_revision(invoice.pk, accounts_user)
        assert new_invoice.line_items.count() == invoice.line_items.count()

    def test_cannot_revise_non_finalized(self, booking_with_pi, accounts_user):
        """Cannot create revision of a non-finalized invoice."""
        booking, _ = booking_with_pi
        invoice = CommercialInvoiceService.create_commercial_invoice(booking.pk, accounts_user)

        with pytest.raises(ValidationError):
            CommercialInvoiceService.create_revision(invoice.pk, accounts_user)
