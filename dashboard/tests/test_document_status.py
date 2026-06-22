"""
Tests for the dashboard document-status endpoint.
"""

import datetime

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APIClient

from bl.models import BillOfLading
from bookings.models import Booking
from invoices.models import CommercialInvoice, PackingList
from master_data.models import (
    Client,
    Commodity,
    Consignee,
    Port,
    Shipper,
    ShippingLine,
)

User = get_user_model()

DOCUMENT_STATUS_URL = '/api/dashboard/document-status/'


@pytest.fixture
def authenticated_client(db):
    """Create an authenticated user and API client."""
    user = User.objects.create_user(username='testuser', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Operations')
    user.groups.add(group)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def master_data(db):
    """Create required master data for bookings."""
    shipping_line = ShippingLine.objects.create(name='Maersk', code='MAEU')
    pol = Port.objects.create(name='Mumbai Port', code='INMUN', country='India')
    pod = Port.objects.create(name='Rotterdam Port', code='NLRTM', country='Netherlands')
    client = Client.objects.create(name='Test Client', email='client@test.com')
    commodity = Commodity.objects.create(name='Electronics', hs_code='8542')
    shipper = Shipper.objects.create(name='Test Shipper', address='123 Ship St')
    consignee = Consignee.objects.create(name='Test Consignee', address='456 Con Ave')
    return {
        'shipping_line': shipping_line,
        'pol': pol,
        'pod': pod,
        'client': client,
        'commodity': commodity,
        'shipper': shipper,
        'consignee': consignee,
    }


def _create_booking(master_data, user, booking_status=Booking.Status.PENDING):
    """Helper to create a booking with required fields."""
    today = datetime.date.today()
    return Booking.objects.create(
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
        status=booking_status,
        created_by=user,
    )


class TestDocumentStatusEndpoint:
    """Tests for GET /api/dashboard/document-status/"""

    def test_unauthenticated_returns_401(self, db):
        client = APIClient()
        response = client.get(DOCUMENT_STATUS_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_database_returns_zeros(self, authenticated_client):
        client, user = authenticated_client
        response = client.get(DOCUMENT_STATUS_URL)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['invoice_pending'] == 0
        assert data['packing_list_pending'] == 0
        assert data['bl_pending'] == 0

    def test_active_booking_without_documents_counts_as_pending(
        self, authenticated_client, master_data
    ):
        client, user = authenticated_client
        _create_booking(master_data, user, Booking.Status.BOOKED)

        response = client.get(DOCUMENT_STATUS_URL)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['invoice_pending'] == 1
        assert data['packing_list_pending'] == 1
        assert data['bl_pending'] == 1

    def test_completed_booking_excluded_from_counts(
        self, authenticated_client, master_data
    ):
        client, user = authenticated_client
        _create_booking(master_data, user, Booking.Status.COMPLETED)

        response = client.get(DOCUMENT_STATUS_URL)
        data = response.json()
        assert data['invoice_pending'] == 0
        assert data['packing_list_pending'] == 0
        assert data['bl_pending'] == 0

    def test_finalized_invoice_removes_from_invoice_pending(
        self, authenticated_client, master_data
    ):
        client, user = authenticated_client
        booking = _create_booking(master_data, user, Booking.Status.SHIPPED)

        # Create a finalized commercial invoice
        CommercialInvoice.objects.create(
            booking=booking,
            status=CommercialInvoice.Status.FINALIZED,
            created_by=user,
        )

        response = client.get(DOCUMENT_STATUS_URL)
        data = response.json()
        assert data['invoice_pending'] == 0
        # Still pending for packing list and BL
        assert data['packing_list_pending'] == 1
        assert data['bl_pending'] == 1

    def test_draft_invoice_still_counts_as_pending(
        self, authenticated_client, master_data
    ):
        client, user = authenticated_client
        booking = _create_booking(master_data, user, Booking.Status.BOOKED)

        # Create a draft commercial invoice (not finalized)
        CommercialInvoice.objects.create(
            booking=booking,
            status=CommercialInvoice.Status.DRAFT,
            created_by=user,
        )

        response = client.get(DOCUMENT_STATUS_URL)
        data = response.json()
        assert data['invoice_pending'] == 1

    def test_finalized_packing_list_removes_from_packing_list_pending(
        self, authenticated_client, master_data
    ):
        client, user = authenticated_client
        booking = _create_booking(master_data, user, Booking.Status.SHIPPED)

        PackingList.objects.create(
            booking=booking,
            status=PackingList.Status.FINALIZED,
            created_by=user,
        )

        response = client.get(DOCUMENT_STATUS_URL)
        data = response.json()
        assert data['packing_list_pending'] == 0
        assert data['invoice_pending'] == 1
        assert data['bl_pending'] == 1

    def test_released_bl_removes_from_bl_pending(
        self, authenticated_client, master_data
    ):
        client, user = authenticated_client
        booking = _create_booking(master_data, user, Booking.Status.SHIPPED)

        BillOfLading.objects.create(
            booking=booking,
            bl_number='BL-001',
            bl_type=BillOfLading.BLType.LINE,
            status=BillOfLading.Status.RELEASED,
            container_number='CONT001',
            vessel_name='Ever Given',
            voyage_number='V001',
            shipper=master_data['shipper'],
            consignee=master_data['consignee'],
            created_by=user,
        )

        response = client.get(DOCUMENT_STATUS_URL)
        data = response.json()
        assert data['bl_pending'] == 0
        assert data['invoice_pending'] == 1
        assert data['packing_list_pending'] == 1

    def test_submitted_bl_still_counts_as_pending(
        self, authenticated_client, master_data
    ):
        client, user = authenticated_client
        booking = _create_booking(master_data, user, Booking.Status.SHIPPED)

        BillOfLading.objects.create(
            booking=booking,
            bl_number='BL-002',
            bl_type=BillOfLading.BLType.DIRECT,
            status=BillOfLading.Status.SUBMITTED,
            container_number='CONT002',
            vessel_name='Ever Given',
            voyage_number='V002',
            shipper=master_data['shipper'],
            consignee=master_data['consignee'],
            created_by=user,
        )

        response = client.get(DOCUMENT_STATUS_URL)
        data = response.json()
        assert data['bl_pending'] == 1

    def test_multiple_active_bookings_counted_correctly(
        self, authenticated_client, master_data
    ):
        client, user = authenticated_client
        booking1 = _create_booking(master_data, user, Booking.Status.BOOKED)
        booking2 = _create_booking(master_data, user, Booking.Status.SHIPPED)
        booking3 = _create_booking(master_data, user, Booking.Status.STUFFING)

        # Finalize invoice only on booking1
        CommercialInvoice.objects.create(
            booking=booking1,
            status=CommercialInvoice.Status.FINALIZED,
            created_by=user,
        )
        # Finalize packing list on booking1 and booking2
        PackingList.objects.create(
            booking=booking1,
            status=PackingList.Status.FINALIZED,
            created_by=user,
        )
        PackingList.objects.create(
            booking=booking2,
            status=PackingList.Status.FINALIZED,
            created_by=user,
        )
        # Release BL on all 3
        for i, b in enumerate([booking1, booking2, booking3], start=1):
            BillOfLading.objects.create(
                booking=b,
                bl_number=f'BL-10{i}',
                bl_type=BillOfLading.BLType.LINE,
                status=BillOfLading.Status.RELEASED,
                container_number=f'CONT10{i}',
                vessel_name='Ever Given',
                voyage_number='V100',
                shipper=master_data['shipper'],
                consignee=master_data['consignee'],
                created_by=user,
            )

        response = client.get(DOCUMENT_STATUS_URL)
        data = response.json()
        # invoice_pending: booking2 and booking3 have no finalized invoice
        assert data['invoice_pending'] == 2
        # packing_list_pending: booking3 has no finalized packing list
        assert data['packing_list_pending'] == 1
        # bl_pending: all 3 have released BL
        assert data['bl_pending'] == 0
