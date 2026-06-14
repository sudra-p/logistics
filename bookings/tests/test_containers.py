"""
Tests for container management endpoints and validation.
"""

import pytest
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from bookings.models import Booking, Container
from master_data.models import (
    Client,
    Commodity,
    ContainerType,
    Port,
    ShippingLine,
)

User = get_user_model()


@pytest.fixture
def ops_user(db):
    """Create an Operations user."""
    user = User.objects.create_user(username='opsuser', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Operations')
    user.groups.add(group)
    return user


@pytest.fixture
def api_client(ops_user):
    """Return an authenticated API client."""
    client = APIClient()
    client.force_authenticate(user=ops_user)
    return client


@pytest.fixture
def master_data(db):
    """Create required master data."""
    shipping_line = ShippingLine.objects.create(name='Maersk', code='MAEU')
    pol = Port.objects.create(name='Mumbai', code='INMUN', country='India')
    pod = Port.objects.create(name='Rotterdam', code='NLRTM', country='Netherlands')
    client = Client.objects.create(name='Test Client', email='client@test.com')
    commodity = Commodity.objects.create(name='Electronics', hs_code='8542')
    container_type = ContainerType.objects.create(name='Dry', code='DRY')
    container_type_2 = ContainerType.objects.create(name='Reefer', code='REF')
    return {
        'shipping_line': shipping_line,
        'pol': pol,
        'pod': pod,
        'client': client,
        'commodity': commodity,
        'container_type': container_type,
        'container_type_2': container_type_2,
    }


@pytest.fixture
def booking(db, ops_user, master_data):
    """Create a booking for testing."""
    booking = Booking(
        booking_date=date(2024, 1, 1),
        booking_validity_date=date(2024, 1, 31),
        forwarding_window_start=date(2024, 1, 5),
        forwarding_window_end=date(2024, 1, 20),
        shipping_line=master_data['shipping_line'],
        pol=master_data['pol'],
        pod=master_data['pod'],
        client=master_data['client'],
        commodity=master_data['commodity'],
        cargo_type=Booking.CargoType.FCL,
        shipment_type='Export',
        stuffing_type='Factory',
        status=Booking.Status.PENDING,
        created_by=ops_user,
    )
    booking.save()
    return booking


@pytest.mark.django_db
class TestAddContainers:
    """Tests for POST /api/bookings/{id}/containers/"""

    def test_add_single_container(self, api_client, booking, master_data):
        """Test successfully adding a single container."""
        url = f'/api/bookings/{booking.id}/containers/'
        data = {
            'container_type': master_data['container_type'].id,
            'container_size': '20FT',
            'container_count': 2,
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == 201
        assert len(response.data) == 1
        assert response.data[0]['container_size'] == '20FT'
        assert response.data[0]['container_count'] == 2
        assert response.data[0]['container_type'] == master_data['container_type'].id

    def test_add_multiple_containers(self, api_client, booking, master_data):
        """Test successfully adding multiple containers as a list."""
        url = f'/api/bookings/{booking.id}/containers/'
        data = [
            {
                'container_type': master_data['container_type'].id,
                'container_size': '20FT',
                'container_count': 3,
            },
            {
                'container_type': master_data['container_type_2'].id,
                'container_size': '40FT_HC',
                'container_count': 1,
                'container_no': 'MSKU1234567',
                'seal_no': 'SEAL001',
            },
        ]
        response = api_client.post(url, data, format='json')

        assert response.status_code == 201
        assert len(response.data) == 2
        assert booking.containers.count() == 2

    def test_reject_count_zero(self, api_client, booking, master_data):
        """Test that container_count of 0 is rejected."""
        url = f'/api/bookings/{booking.id}/containers/'
        data = {
            'container_type': master_data['container_type'].id,
            'container_size': '20FT',
            'container_count': 0,
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == 400

    def test_reject_negative_count(self, api_client, booking, master_data):
        """Test that negative container_count is rejected."""
        url = f'/api/bookings/{booking.id}/containers/'
        data = {
            'container_type': master_data['container_type'].id,
            'container_size': '20FT',
            'container_count': -1,
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == 400

    def test_reject_invalid_container_size(self, api_client, booking, master_data):
        """Test that an invalid container size is rejected."""
        url = f'/api/bookings/{booking.id}/containers/'
        data = {
            'container_type': master_data['container_type'].id,
            'container_size': '50FT',
            'container_count': 1,
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == 400

    def test_reject_invalid_container_type(self, api_client, booking, master_data):
        """Test that a non-existent container_type ID is rejected."""
        url = f'/api/bookings/{booking.id}/containers/'
        data = {
            'container_type': 99999,
            'container_size': '20FT',
            'container_count': 1,
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == 400

    def test_enforce_max_50_containers(self, api_client, booking, master_data):
        """Test that adding containers beyond 50 is rejected."""
        # Add 50 containers first
        url = f'/api/bookings/{booking.id}/containers/'
        batch = [
            {
                'container_type': master_data['container_type'].id,
                'container_size': '20FT',
                'container_count': 1,
            }
            for _ in range(50)
        ]
        response = api_client.post(url, batch, format='json')
        assert response.status_code == 201
        assert booking.containers.count() == 50

        # Try to add one more
        data = {
            'container_type': master_data['container_type'].id,
            'container_size': '20FT',
            'container_count': 1,
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == 400
        assert 'containers' in response.data

    def test_booking_not_found(self, api_client, master_data):
        """Test 404 for non-existent booking."""
        url = '/api/bookings/99999/containers/'
        data = {
            'container_type': master_data['container_type'].id,
            'container_size': '20FT',
            'container_count': 1,
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == 404

    def test_all_valid_sizes_accepted(self, api_client, booking, master_data):
        """Test that all valid container sizes are accepted."""
        url = f'/api/bookings/{booking.id}/containers/'
        for size in ['20FT', '40FT', '40FT_HC', '45FT']:
            data = {
                'container_type': master_data['container_type'].id,
                'container_size': size,
                'container_count': 1,
            }
            response = api_client.post(url, data, format='json')
            assert response.status_code == 201, f'Size {size} should be accepted'


@pytest.mark.django_db
class TestRemoveContainer:
    """Tests for DELETE /api/bookings/{id}/containers/{cid}/"""

    def test_remove_container_success(self, api_client, booking, master_data):
        """Test successfully removing a container."""
        # Add a container first
        url = f'/api/bookings/{booking.id}/containers/'
        data = {
            'container_type': master_data['container_type'].id,
            'container_size': '20FT',
            'container_count': 2,
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == 201
        container_id = response.data[0]['id']

        # Delete the container
        delete_url = f'/api/bookings/{booking.id}/containers/{container_id}/'
        response = api_client.delete(delete_url)

        assert response.status_code == 204
        assert booking.containers.count() == 0

    def test_remove_nonexistent_container(self, api_client, booking):
        """Test 404 for non-existent container."""
        delete_url = f'/api/bookings/{booking.id}/containers/99999/'
        response = api_client.delete(delete_url)

        assert response.status_code == 404

    def test_remove_container_wrong_booking(self, api_client, booking, master_data, ops_user):
        """Test 404 when container belongs to a different booking."""
        # Add a container to the first booking
        url = f'/api/bookings/{booking.id}/containers/'
        data = {
            'container_type': master_data['container_type'].id,
            'container_size': '20FT',
            'container_count': 1,
        }
        response = api_client.post(url, data, format='json')
        container_id = response.data[0]['id']

        # Create another booking
        booking2 = Booking(
            booking_date=date(2024, 2, 1),
            booking_validity_date=date(2024, 2, 28),
            forwarding_window_start=date(2024, 2, 5),
            forwarding_window_end=date(2024, 2, 20),
            shipping_line=master_data['shipping_line'],
            pol=master_data['pol'],
            pod=master_data['pod'],
            client=master_data['client'],
            commodity=master_data['commodity'],
            cargo_type=Booking.CargoType.FCL,
            shipment_type='Export',
            stuffing_type='Factory',
            status=Booking.Status.PENDING,
            created_by=ops_user,
        )
        booking2.save()

        # Try to delete container from wrong booking
        delete_url = f'/api/bookings/{booking2.id}/containers/{container_id}/'
        response = api_client.delete(delete_url)

        assert response.status_code == 404


@pytest.mark.django_db
class TestListContainers:
    """Tests for GET /api/bookings/{id}/containers/"""

    def test_list_empty(self, api_client, booking):
        """Test listing containers when none exist."""
        url = f'/api/bookings/{booking.id}/containers/'
        response = api_client.get(url)

        assert response.status_code == 200
        assert response.data == []

    def test_list_with_containers(self, api_client, booking, master_data):
        """Test listing containers after adding some."""
        url = f'/api/bookings/{booking.id}/containers/'
        data = [
            {
                'container_type': master_data['container_type'].id,
                'container_size': '20FT',
                'container_count': 2,
            },
            {
                'container_type': master_data['container_type_2'].id,
                'container_size': '40FT',
                'container_count': 1,
            },
        ]
        api_client.post(url, data, format='json')

        response = api_client.get(url)

        assert response.status_code == 200
        assert len(response.data) == 2
