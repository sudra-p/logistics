"""
Tests for the dashboard KPI endpoint.
"""

import datetime

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APIClient

from bookings.models import Booking, Container
from inventory.models import StockItem
from master_data.models import Client, Commodity, ContainerType, Port, ShippingLine
from proforma.models import ProformaInvoice

User = get_user_model()

KPI_URL = '/api/dashboard/kpis/'


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
    """Create required master data for bookings and PIs."""
    shipping_line = ShippingLine.objects.create(name='Maersk', code='MAEU')
    pol = Port.objects.create(name='Mumbai Port', code='INMUN', country='India')
    pod = Port.objects.create(name='Rotterdam Port', code='NLRTM', country='Netherlands')
    client = Client.objects.create(name='Test Client', email='client@test.com')
    commodity = Commodity.objects.create(name='Electronics', hs_code='8542')
    container_type = ContainerType.objects.create(name='Dry', code='DRY')
    return {
        'shipping_line': shipping_line,
        'pol': pol,
        'pod': pod,
        'client': client,
        'commodity': commodity,
        'container_type': container_type,
    }


class TestKPIEndpoint:
    """Tests for GET /api/dashboard/kpis/"""

    def test_unauthenticated_returns_401(self, db):
        client = APIClient()
        response = client.get(KPI_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_database_returns_zeros(self, authenticated_client):
        client, user = authenticated_client
        response = client.get(KPI_URL)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['total_pis'] == 0
        assert data['pending_payments'] == 0
        assert data['active_shipments'] == 0
        assert data['containers_in_transit'] == 0
        assert data['stock_available'] == 0

    def test_total_pis_counts_all(self, authenticated_client, master_data):
        client, user = authenticated_client
        # Create PIs in different statuses
        for s in [ProformaInvoice.Status.DRAFT, ProformaInvoice.Status.SENT, ProformaInvoice.Status.PAID]:
            ProformaInvoice.objects.create(
                date=datetime.date.today(),
                customer=master_data['client'],
                currency='USD',
                payment_terms='Net 30',
                expected_shipment_date=datetime.date.today(),
                status=s,
                created_by=user,
            )
        response = client.get(KPI_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()['total_pis'] == 3

    def test_pending_payments_counts_payment_pending_only(self, authenticated_client, master_data):
        client, user = authenticated_client
        ProformaInvoice.objects.create(
            date=datetime.date.today(),
            customer=master_data['client'],
            currency='USD',
            payment_terms='Net 30',
            expected_shipment_date=datetime.date.today(),
            status=ProformaInvoice.Status.PAYMENT_PENDING,
            created_by=user,
        )
        ProformaInvoice.objects.create(
            date=datetime.date.today(),
            customer=master_data['client'],
            currency='USD',
            payment_terms='Net 30',
            expected_shipment_date=datetime.date.today(),
            status=ProformaInvoice.Status.DRAFT,
            created_by=user,
        )
        response = client.get(KPI_URL)
        assert response.json()['pending_payments'] == 1

    def test_active_shipments_excludes_completed(self, authenticated_client, master_data):
        client, user = authenticated_client
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
            'created_by': user,
        }
        Booking.objects.create(status=Booking.Status.PENDING, **base_kwargs)
        Booking.objects.create(status=Booking.Status.BOOKED, **base_kwargs)
        Booking.objects.create(status=Booking.Status.COMPLETED, **base_kwargs)

        response = client.get(KPI_URL)
        assert response.json()['active_shipments'] == 2

    def test_containers_in_transit(self, authenticated_client, master_data):
        client, user = authenticated_client
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
            'created_by': user,
        }
        booked = Booking.objects.create(status=Booking.Status.BOOKED, **base_kwargs)
        shipped = Booking.objects.create(status=Booking.Status.SHIPPED, **base_kwargs)
        pending = Booking.objects.create(status=Booking.Status.PENDING, **base_kwargs)
        completed = Booking.objects.create(status=Booking.Status.COMPLETED, **base_kwargs)

        ct = master_data['container_type']
        # Containers on booked/shipped bookings count
        Container.objects.create(booking=booked, container_type=ct, container_size='20FT', container_count=1)
        Container.objects.create(booking=shipped, container_type=ct, container_size='40FT', container_count=1)
        # Containers on pending/completed bookings do not count
        Container.objects.create(booking=pending, container_type=ct, container_size='20FT', container_count=1)
        Container.objects.create(booking=completed, container_type=ct, container_size='20FT', container_count=1)

        response = client.get(KPI_URL)
        assert response.json()['containers_in_transit'] == 2

    def test_stock_available_sums_all(self, authenticated_client):
        client, user = authenticated_client
        StockItem.objects.create(product_name='Widget A', available_stock=100)
        StockItem.objects.create(product_name='Widget B', available_stock=250)
        StockItem.objects.create(product_name='Widget C', available_stock=0)

        response = client.get(KPI_URL)
        assert response.json()['stock_available'] == 350
