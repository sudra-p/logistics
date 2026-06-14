"""
Tests for booking creation endpoint and service layer.
"""

import datetime

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APIClient

from bookings.models import Booking
from master_data.models import (
    Client,
    Commodity,
    Port,
    ShippingLine,
)

User = get_user_model()


@pytest.fixture
def ops_user(db):
    """Create an Operations group user."""
    user = User.objects.create_user(username='ops_user', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Operations')
    user.groups.add(group)
    return user


@pytest.fixture
def admin_user(db):
    """Create an Admin group user."""
    user = User.objects.create_user(username='admin_user', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Admin')
    user.groups.add(group)
    return user


@pytest.fixture
def sales_user(db):
    """Create a Sales group user (no modify permission)."""
    user = User.objects.create_user(username='sales_user', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Sales')
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
def valid_booking_data(master_data):
    """Return valid booking creation payload with all mandatory fields."""
    return {
        'booking_date': '2024-03-01',
        'booking_validity_date': '2024-03-15',
        'forwarding_window_start': '2024-03-05',
        'forwarding_window_end': '2024-03-10',
        'shipping_line': master_data['shipping_line'].pk,
        'pol': master_data['pol'].pk,
        'pod': master_data['pod'].pk,
        'client': master_data['client'].pk,
        'commodity': master_data['commodity'].pk,
        'cargo_type': 'FCL',
        'shipment_type': 'Direct',
        'stuffing_type': 'Factory',
    }


@pytest.fixture
def api_client():
    return APIClient()


class TestBookingCreationSuccess:
    """Tests for successful booking creation."""

    def test_create_booking_with_mandatory_fields(
        self, api_client, ops_user, valid_booking_data
    ):
        """Successful creation with all mandatory fields returns 201 and job_number."""
        api_client.force_authenticate(user=ops_user)
        response = api_client.post('/api/bookings/', valid_booking_data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert 'job_number' in response.data
        assert response.data['job_number'].startswith('JOB-')
        assert response.data['status'] == 'PENDING'
        assert response.data['created_by'] == ops_user.pk

    def test_create_booking_admin_user(
        self, api_client, admin_user, valid_booking_data
    ):
        """Admin users can also create bookings."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.post('/api/bookings/', valid_booking_data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] == 'PENDING'

    def test_job_number_generated_on_success(
        self, api_client, ops_user, valid_booking_data
    ):
        """Job number is generated sequentially on successful creation."""
        api_client.force_authenticate(user=ops_user)

        response1 = api_client.post('/api/bookings/', valid_booking_data, format='json')
        response2 = api_client.post('/api/bookings/', valid_booking_data, format='json')

        assert response1.status_code == status.HTTP_201_CREATED
        assert response2.status_code == status.HTTP_201_CREATED
        # Both should have different job numbers
        assert response1.data['job_number'] != response2.data['job_number']


class TestBookingCreationValidation:
    """Tests for validation errors during booking creation."""

    def test_missing_mandatory_field(self, api_client, ops_user, valid_booking_data):
        """Missing a mandatory field returns 400 validation error."""
        api_client.force_authenticate(user=ops_user)
        del valid_booking_data['booking_date']

        response = api_client.post('/api/bookings/', valid_booking_data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'booking_date' in response.data

    def test_invalid_date_ordering(self, api_client, ops_user, valid_booking_data):
        """Booking validity date before booking date returns validation error."""
        api_client.force_authenticate(user=ops_user)
        valid_booking_data['booking_validity_date'] = '2024-02-01'  # Before booking_date

        response = api_client.post('/api/bookings/', valid_booking_data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'booking_validity_date' in response.data

    def test_invalid_forwarding_window(self, api_client, ops_user, valid_booking_data):
        """Forwarding window end before start returns validation error."""
        api_client.force_authenticate(user=ops_user)
        valid_booking_data['forwarding_window_end'] = '2024-03-01'
        valid_booking_data['forwarding_window_start'] = '2024-03-10'

        response = api_client.post('/api/bookings/', valid_booking_data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'forwarding_window_end' in response.data

    def test_haz_fields_required_when_is_haz_true(
        self, api_client, ops_user, valid_booking_data
    ):
        """HAZ fields must be provided when is_haz=True."""
        api_client.force_authenticate(user=ops_user)
        valid_booking_data['is_haz'] = True
        # Not providing haz_class, haz_uin, haz_group

        response = api_client.post('/api/bookings/', valid_booking_data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'haz_class' in response.data
        assert 'haz_uin' in response.data
        assert 'haz_group' in response.data

    def test_invalid_fk_reference(self, api_client, ops_user, valid_booking_data):
        """Non-existent FK ID returns validation error."""
        api_client.force_authenticate(user=ops_user)
        valid_booking_data['shipping_line'] = 99999  # Non-existent

        response = api_client.post('/api/bookings/', valid_booking_data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'shipping_line' in response.data

    def test_failed_validation_does_not_create_record(
        self, api_client, ops_user, valid_booking_data
    ):
        """Failed validation should not create a booking or consume a job number."""
        api_client.force_authenticate(user=ops_user)
        del valid_booking_data['booking_date']  # Make it invalid

        initial_count = Booking.objects.count()
        response = api_client.post('/api/bookings/', valid_booking_data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Booking.objects.count() == initial_count


class TestBookingPermissions:
    """Tests for permission enforcement on booking endpoints."""

    def test_unauthenticated_user_denied(self, api_client, valid_booking_data):
        """Unauthenticated request returns 401."""
        response = api_client.post('/api/bookings/', valid_booking_data, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_sales_user_cannot_create(
        self, api_client, sales_user, valid_booking_data
    ):
        """Sales user (no CanModifyBooking) cannot create bookings."""
        api_client.force_authenticate(user=sales_user)
        response = api_client.post('/api/bookings/', valid_booking_data, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_sales_user_can_view(self, api_client, sales_user, ops_user, valid_booking_data):
        """Sales user can view bookings (CanViewBooking)."""
        # First create a booking as ops user
        api_client.force_authenticate(user=ops_user)
        api_client.post('/api/bookings/', valid_booking_data, format='json')

        # Now try to list as sales user
        api_client.force_authenticate(user=sales_user)
        response = api_client.get('/api/bookings/')

        assert response.status_code == status.HTTP_200_OK
