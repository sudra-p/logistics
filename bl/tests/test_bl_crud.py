"""
Tests for Bill of Lading creation with auto-fill, status transitions, validation.
Task 25.9.
"""

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.exceptions import ValidationError

from bl.models import BillOfLading
from bl.services import BillOfLadingService
from bookings.models import Booking, Container
from invoices.models import CommercialInvoice, CommercialInvoiceLineItem
from invoices.services import CommercialInvoiceService
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
from proforma.models import ProformaInvoice, ProformaLineItem

User = get_user_model()


@pytest.fixture
def ops_user(db):
    user = User.objects.create_user(username='ops_user', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Operations')
    user.groups.add(group)
    return user


@pytest.fixture
def master_data(db):
    shipping_line = ShippingLine.objects.create(name='Maersk', code='MAEU')
    pol = Port.objects.create(name='Mumbai Port', code='INMUN', country='India')
    pod = Port.objects.create(name='Rotterdam Port', code='NLRTM', country='Netherlands')
    client = Client.objects.create(name='Test Client', email='client@test.com')
    commodity = Commodity.objects.create(name='Electronics', hs_code='8542')
    container_type = ContainerType.objects.create(name='Dry', code='DRY')
    vessel = Vessel.objects.create(name='Ever Given', imo_number='9811000')
    shipper = Shipper.objects.create(name='Test Shipper')
    consignee = Consignee.objects.create(name='Test Consignee')
    return {
        'shipping_line': shipping_line,
        'pol': pol,
        'pod': pod,
        'client': client,
        'commodity': commodity,
        'container_type': container_type,
        'vessel': vessel,
        'shipper': shipper,
        'consignee': consignee,
    }


@pytest.fixture
def booking_with_docs(master_data, ops_user):
    """Create a booking with vessel, containers, and finalized commercial invoice."""
    today = datetime.date.today()
    booking = Booking.objects.create(
        status=Booking.Status.SHIPPED,
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
        vessel=master_data['vessel'],
        voyage='V001E',
        shipper=master_data['shipper'],
        consignee=master_data['consignee'],
        created_by=ops_user,
    )
    Container.objects.create(
        booking=booking,
        container_type=master_data['container_type'],
        container_size='20FT',
        container_count=1,
        container_no='MSKU1234567',
        stuffing_status='STUFFED',
    )
    # Create finalized commercial invoice
    invoice = CommercialInvoice.objects.create(
        booking=booking,
        revision=1,
        status=CommercialInvoice.Status.FINALIZED,
        created_by=ops_user,
    )
    CommercialInvoiceLineItem.objects.create(
        commercial_invoice=invoice,
        product_name='Widget A',
        quantity=Decimal('100.000'),
        rate=Decimal('10.00'),
        amount=Decimal('1000.00'),
    )
    return booking


@pytest.mark.django_db
class TestBLCreation:
    """Tests for BL creation and auto-fill."""

    def test_create_bl_with_auto_fill(self, booking_with_docs, master_data, ops_user):
        """BL auto-fills vessel, voyage, container, shipper, consignee from booking."""
        bl = BillOfLadingService.create_bl(
            booking_with_docs.pk,
            ops_user,
            data={
                'bl_number': 'BL-001',
                'bl_type': 'LINE',
            },
        )

        assert bl.pk is not None
        assert bl.status == BillOfLading.Status.DRAFT
        assert bl.vessel_name == 'Ever Given'
        assert bl.voyage_number == 'V001E'
        assert bl.container_number == 'MSKU1234567'
        assert bl.shipper == master_data['shipper']
        assert bl.consignee == master_data['consignee']

    def test_cargo_description_auto_filled(self, booking_with_docs, master_data, ops_user):
        """BL cargo description auto-populated from commercial invoice items."""
        bl = BillOfLadingService.create_bl(
            booking_with_docs.pk,
            ops_user,
            data={
                'bl_number': 'BL-002',
                'bl_type': 'DIRECT',
            },
        )
        assert 'Widget A' in bl.cargo_description

    def test_create_bl_with_explicit_values(self, booking_with_docs, master_data, ops_user):
        """Can provide explicit values that override auto-fill."""
        bl = BillOfLadingService.create_bl(
            booking_with_docs.pk,
            ops_user,
            data={
                'bl_number': 'BL-003',
                'bl_type': 'LINE',
                'vessel_name': 'Custom Vessel',
                'voyage_number': 'CV001',
                'container_number': 'ABCD1234567',
                'shipper': master_data['shipper'],
                'consignee': master_data['consignee'],
            },
        )
        assert bl.vessel_name == 'Custom Vessel'
        assert bl.voyage_number == 'CV001'
        assert bl.container_number == 'ABCD1234567'

    def test_bl_requires_shipper_and_consignee(self, master_data, ops_user):
        """BL creation fails if shipper/consignee cannot be resolved."""
        today = datetime.date.today()
        # Create booking without shipper/consignee
        booking = Booking.objects.create(
            status=Booking.Status.SHIPPED,
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
            created_by=ops_user,
        )

        with pytest.raises(ValidationError):
            BillOfLadingService.create_bl(
                booking.pk,
                ops_user,
                data={'bl_number': 'BL-004', 'bl_type': 'LINE'},
            )


@pytest.mark.django_db
class TestBLStatusTransitions:
    """Tests for BL status transitions."""

    def test_draft_to_submitted(self, booking_with_docs, master_data, ops_user):
        """DRAFT -> SUBMITTED is valid."""
        bl = BillOfLadingService.create_bl(
            booking_with_docs.pk,
            ops_user,
            data={'bl_number': 'BL-010', 'bl_type': 'LINE'},
        )
        updated = BillOfLadingService.change_bl_status(bl.pk, 'SUBMITTED', ops_user)
        assert updated.status == BillOfLading.Status.SUBMITTED

    def test_submitted_to_released(self, booking_with_docs, master_data, ops_user):
        """SUBMITTED -> RELEASED is valid."""
        bl = BillOfLadingService.create_bl(
            booking_with_docs.pk,
            ops_user,
            data={'bl_number': 'BL-011', 'bl_type': 'LINE'},
        )
        BillOfLadingService.change_bl_status(bl.pk, 'SUBMITTED', ops_user)
        updated = BillOfLadingService.change_bl_status(bl.pk, 'RELEASED', ops_user)
        assert updated.status == BillOfLading.Status.RELEASED

    def test_draft_to_released_rejected(self, booking_with_docs, master_data, ops_user):
        """DRAFT -> RELEASED is not allowed (must go through SUBMITTED)."""
        bl = BillOfLadingService.create_bl(
            booking_with_docs.pk,
            ops_user,
            data={'bl_number': 'BL-012', 'bl_type': 'LINE'},
        )
        with pytest.raises(ValidationError):
            BillOfLadingService.change_bl_status(bl.pk, 'RELEASED', ops_user)

    def test_released_is_terminal(self, booking_with_docs, master_data, ops_user):
        """RELEASED is a terminal status."""
        bl = BillOfLadingService.create_bl(
            booking_with_docs.pk,
            ops_user,
            data={'bl_number': 'BL-013', 'bl_type': 'LINE'},
        )
        BillOfLadingService.change_bl_status(bl.pk, 'SUBMITTED', ops_user)
        BillOfLadingService.change_bl_status(bl.pk, 'RELEASED', ops_user)

        with pytest.raises(ValidationError):
            BillOfLadingService.change_bl_status(bl.pk, 'DRAFT', ops_user)

    def test_backward_transition_rejected(self, booking_with_docs, master_data, ops_user):
        """SUBMITTED -> DRAFT is not allowed."""
        bl = BillOfLadingService.create_bl(
            booking_with_docs.pk,
            ops_user,
            data={'bl_number': 'BL-014', 'bl_type': 'LINE'},
        )
        BillOfLadingService.change_bl_status(bl.pk, 'SUBMITTED', ops_user)

        with pytest.raises(ValidationError):
            BillOfLadingService.change_bl_status(bl.pk, 'DRAFT', ops_user)


@pytest.mark.django_db
class TestBLValidation:
    """Tests for BL field validation."""

    def test_bl_number_unique(self, booking_with_docs, master_data, ops_user):
        """Cannot create two BLs with the same bl_number."""
        from django.db import IntegrityError

        BillOfLadingService.create_bl(
            booking_with_docs.pk,
            ops_user,
            data={'bl_number': 'BL-UNIQUE', 'bl_type': 'LINE'},
        )

        with pytest.raises((ValidationError, IntegrityError)):
            BillOfLadingService.create_bl(
                booking_with_docs.pk,
                ops_user,
                data={'bl_number': 'BL-UNIQUE', 'bl_type': 'DIRECT'},
            )

    def test_only_draft_bl_editable(self, booking_with_docs, master_data, ops_user):
        """Only DRAFT BLs can be edited."""
        bl = BillOfLadingService.create_bl(
            booking_with_docs.pk,
            ops_user,
            data={'bl_number': 'BL-015', 'bl_type': 'LINE'},
        )
        BillOfLadingService.change_bl_status(bl.pk, 'SUBMITTED', ops_user)

        with pytest.raises(ValidationError):
            BillOfLadingService.update_bl(bl.pk, ops_user, data={'notify_party': 'New Party'})
