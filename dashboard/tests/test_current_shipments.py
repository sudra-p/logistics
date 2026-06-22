"""
Tests for the dashboard current-shipments endpoint.
"""

import datetime

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from bookings.models import Booking, Container
from master_data.models import Client, Commodity, ContainerType, Port, ShippingLine

User = get_user_model()

CURRENT_SHIPMENTS_URL = '/api/dashboard/current-shipments/'


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
    """Create required master data for booking creation."""
    shipping_line = ShippingLine.objects.create(name='Maersk', code='MAEU')
    pol = Port.objects.create(name='Mumbai Port', code='INMUN', country='India')
    pod = Port.objects.create(name='Rotterdam Port', code='NLRTM', country='Netherlands')
    client_entity = Client.objects.create(name='Acme Corp', email='acme@test.com')
    commodity = Commodity.objects.create(name='Electronics', hs_code='8542')
    container_type = ContainerType.objects.create(name='Dry', code='DRY')
    return {
        'shipping_line': shipping_line,
        'pol': pol,
        'pod': pod,
        'client': client_entity,
        'commodity': commodity,
        'container_type': container_type,
    }


def create_booking(user, master_data, status_val=Booking.Status.PENDING, **kwargs):
    """Helper to create a Booking with required fields."""
    defaults = {
        'booking_date': datetime.date.today(),
        'booking_validity_date': datetime.date.today() + datetime.timedelta(days=14),
        'forwarding_window_start': datetime.date.today(),
        'forwarding_window_end': datetime.date.today() + datetime.timedelta(days=7),
        'shipping_line': master_data['shipping_line'],
        'pol': master_data['pol'],
        'pod': master_data['pod'],
        'client': master_data['client'],
        'commodity': master_data['commodity'],
        'cargo_type': Booking.CargoType.FCL,
        'shipment_type': 'Export',
        'stuffing_type': 'Factory',
        'status': status_val,
        'created_by': user,
    }
    defaults.update(kwargs)
    return Booking.objects.create(**defaults)


class TestCurrentShipmentsEndpoint:
    """Tests for GET /api/dashboard/current-shipments/"""

    def test_unauthenticated_returns_401(self, db):
        client = APIClient()
        response = client.get(CURRENT_SHIPMENTS_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_database_returns_empty_list(self, authenticated_client):
        client, user = authenticated_client
        response = client.get(CURRENT_SHIPMENTS_URL)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['results'] == []
        assert data['count'] == 0

    def test_excludes_completed_bookings(self, authenticated_client, master_data):
        client, user = authenticated_client
        create_booking(user, master_data, status_val=Booking.Status.COMPLETED)
        response = client.get(CURRENT_SHIPMENTS_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()['count'] == 0

    def test_includes_active_bookings(self, authenticated_client, master_data):
        client, user = authenticated_client
        active_statuses = [
            Booking.Status.PENDING,
            Booking.Status.BOOKED,
            Booking.Status.STUFFING,
            Booking.Status.SHIPPED,
        ]
        for s in active_statuses:
            create_booking(user, master_data, status_val=s)
        response = client.get(CURRENT_SHIPMENTS_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()['count'] == 4

    def test_response_fields(self, authenticated_client, master_data):
        client, user = authenticated_client
        etd = timezone.now()
        eta = timezone.now() + datetime.timedelta(days=20)
        booking = create_booking(
            user, master_data,
            status_val=Booking.Status.BOOKED,
            etd_pol=etd,
            eta_destination=eta,
        )
        # Add a container
        Container.objects.create(
            booking=booking,
            container_type=master_data['container_type'],
            container_size=Container.Size.FT_20,
            container_count=1,
            container_no='MSKU1234567',
        )
        response = client.get(CURRENT_SHIPMENTS_URL)
        assert response.status_code == status.HTTP_200_OK
        result = response.json()['results'][0]
        assert 'job_number' in result
        assert result['customer'] == 'Acme Corp'
        assert result['status'] == 'BOOKED'
        assert result['etd'] is not None
        assert result['eta'] is not None
        assert len(result['containers']) == 1
        assert result['containers'][0]['container_no'] == 'MSKU1234567'
        assert result['containers'][0]['container_size'] == '20FT'
        assert result['containers'][0]['container_count'] == 1

    def test_pagination(self, authenticated_client, master_data):
        client, user = authenticated_client
        # Create 30 bookings (default page_size is 25)
        for _ in range(30):
            create_booking(user, master_data, status_val=Booking.Status.PENDING)
        response = client.get(CURRENT_SHIPMENTS_URL)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['count'] == 30
        assert len(data['results']) == 25
        assert data['next'] is not None
