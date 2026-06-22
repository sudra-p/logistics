"""
Tests for the dashboard ready-for-booking endpoint.
"""

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APIClient

from bookings.models import Booking
from master_data.models import (
    Client,
    Commodity,
    ContainerType,
    Port,
    ShippingLine,
)
from proforma.models import ProformaInvoice

User = get_user_model()

READY_FOR_BOOKING_URL = '/api/dashboard/ready-for-booking/'


@pytest.fixture
def operations_client(db):
    """Create an Operations user and API client."""
    user = User.objects.create_user(username='ops_user', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Operations')
    user.groups.add(group)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def admin_client_auth(db):
    """Create an Admin user and API client."""
    user = User.objects.create_user(username='admin_user', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Admin')
    user.groups.add(group)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def accounts_client(db):
    """Create an Accounts user and API client (should NOT have access)."""
    user = User.objects.create_user(username='acc_user', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Accounts')
    user.groups.add(group)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def test_client_entity(db):
    """Create a Client master data record."""
    return Client.objects.create(name='Acme Corp', email='acme@test.com')


@pytest.fixture
def booking_dependencies(db, test_client_entity):
    """Create required master data for Booking creation."""
    shipping_line = ShippingLine.objects.create(name='Maersk')
    pol = Port.objects.create(name='Mumbai', code='INMUN')
    pod = Port.objects.create(name='Rotterdam', code='NLRTM')
    commodity = Commodity.objects.create(name='Electronics')
    container_type = ContainerType.objects.create(name='Dry', code='DRY')
    return {
        'shipping_line': shipping_line,
        'pol': pol,
        'pod': pod,
        'client': test_client_entity,
        'commodity': commodity,
        'container_type': container_type,
    }


class TestReadyForBookingEndpoint:
    """Tests for GET /api/dashboard/ready-for-booking/"""

    def test_unauthenticated_returns_401(self, db):
        client = APIClient()
        response = client.get(READY_FOR_BOOKING_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_accounts_user_returns_403(self, accounts_client):
        client, _ = accounts_client
        response = client.get(READY_FOR_BOOKING_URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_operations_user_has_access(self, operations_client):
        client, _ = operations_client
        response = client.get(READY_FOR_BOOKING_URL)
        assert response.status_code == status.HTTP_200_OK

    def test_admin_user_has_access(self, admin_client_auth):
        client, _ = admin_client_auth
        response = client.get(READY_FOR_BOOKING_URL)
        assert response.status_code == status.HTTP_200_OK

    def test_empty_database_returns_empty_list(self, operations_client):
        client, _ = operations_client
        response = client.get(READY_FOR_BOOKING_URL)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['results'] == []
        assert data['count'] == 0

    def test_includes_paid_pi_with_no_bookings(
        self, operations_client, test_client_entity
    ):
        client, user = operations_client
        ProformaInvoice.objects.create(
            date=datetime.date.today(),
            customer=test_client_entity,
            currency='USD',
            payment_terms='Net 30',
            expected_shipment_date=datetime.date.today(),
            total_amount=Decimal('10000.00'),
            status=ProformaInvoice.Status.PAID,
            created_by=user,
        )
        response = client.get(READY_FOR_BOOKING_URL)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['count'] == 1
        result = data['results'][0]
        assert result['customer_name'] == 'Acme Corp'
        assert result['amount'] == '10000.00'
        assert result['status'] == 'PAID'

    def test_excludes_paid_pi_with_linked_booking(
        self, operations_client, test_client_entity, booking_dependencies
    ):
        client, user = operations_client
        pi = ProformaInvoice.objects.create(
            date=datetime.date.today(),
            customer=test_client_entity,
            currency='USD',
            payment_terms='Net 30',
            expected_shipment_date=datetime.date.today(),
            total_amount=Decimal('10000.00'),
            status=ProformaInvoice.Status.PAID,
            created_by=user,
        )
        deps = booking_dependencies
        Booking.objects.create(
            proforma_invoice=pi,
            booking_date=datetime.date.today(),
            booking_validity_date=datetime.date.today(),
            forwarding_window_start=datetime.date.today(),
            forwarding_window_end=datetime.date.today(),
            shipping_line=deps['shipping_line'],
            pol=deps['pol'],
            pod=deps['pod'],
            client=deps['client'],
            commodity=deps['commodity'],
            cargo_type=Booking.CargoType.FCL,
            shipment_type='Export',
            stuffing_type='Factory',
            created_by=user,
        )
        response = client.get(READY_FOR_BOOKING_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()['count'] == 0

    def test_excludes_non_paid_statuses(
        self, operations_client, test_client_entity
    ):
        client, user = operations_client
        for s in [
            ProformaInvoice.Status.DRAFT,
            ProformaInvoice.Status.SENT,
            ProformaInvoice.Status.APPROVED,
            ProformaInvoice.Status.PAYMENT_PENDING,
        ]:
            ProformaInvoice.objects.create(
                date=datetime.date.today(),
                customer=test_client_entity,
                currency='USD',
                payment_terms='Net 30',
                expected_shipment_date=datetime.date.today(),
                status=s,
                created_by=user,
            )
        response = client.get(READY_FOR_BOOKING_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()['count'] == 0

    def test_response_fields(self, operations_client, test_client_entity):
        client, user = operations_client
        ProformaInvoice.objects.create(
            date=datetime.date.today(),
            customer=test_client_entity,
            currency='USD',
            payment_terms='Net 30',
            expected_shipment_date=datetime.date.today(),
            total_amount=Decimal('7500.00'),
            status=ProformaInvoice.Status.PAID,
            created_by=user,
        )
        response = client.get(READY_FOR_BOOKING_URL)
        assert response.status_code == status.HTTP_200_OK
        result = response.json()['results'][0]
        assert 'pi_number' in result
        assert 'customer_name' in result
        assert 'amount' in result
        assert 'status' in result
