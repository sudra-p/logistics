"""
Tests for the booking update endpoint (PUT/PATCH /api/bookings/{id}/).
Covers Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
"""

import datetime

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APIClient

from bookings.models import Booking
from master_data.models import Client, Commodity, Port, ShippingLine

User = get_user_model()


@pytest.fixture
def ops_user(db):
    """Create an Operations user with appropriate group."""
    user = User.objects.create_user(username='ops_user', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Operations')
    user.groups.add(group)
    return user


@pytest.fixture
def admin_user(db):
    """Create an Admin user with appropriate group."""
    user = User.objects.create_user(username='admin_user', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Admin')
    user.groups.add(group)
    return user


@pytest.fixture
def sales_user(db):
    """Create a Sales user with appropriate group."""
    user = User.objects.create_user(username='sales_user', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Sales')
    user.groups.add(group)
    return user


@pytest.fixture
def master_data(db):
    """Create master data needed for booking creation."""
    client = Client.objects.create(name='Test Client')
    shipping_line = ShippingLine.objects.create(name='Test Line')
    pol = Port.objects.create(name='Mumbai Port', code='INMUN')
    pod = Port.objects.create(name='Singapore Port', code='SGSIN')
    commodity = Commodity.objects.create(name='Electronics')
    return {
        'client': client,
        'shipping_line': shipping_line,
        'pol': pol,
        'pod': pod,
        'commodity': commodity,
    }


@pytest.fixture
def pending_booking(db, ops_user, master_data):
    """Create a pending booking for testing updates."""
    booking = Booking(
        status=Booking.Status.PENDING,
        created_by=ops_user,
        booking_date=datetime.date(2024, 6, 1),
        booking_validity_date=datetime.date(2024, 6, 30),
        forwarding_window_start=datetime.date(2024, 6, 10),
        forwarding_window_end=datetime.date(2024, 6, 20),
        shipping_line=master_data['shipping_line'],
        pol=master_data['pol'],
        pod=master_data['pod'],
        client=master_data['client'],
        commodity=master_data['commodity'],
        cargo_type=Booking.CargoType.FCL,
        shipment_type='Direct',
        stuffing_type='Factory',
    )
    booking.save()
    return booking


@pytest.fixture
def completed_booking(db, ops_user, master_data):
    """Create a completed booking for testing rejection."""
    booking = Booking(
        status=Booking.Status.COMPLETED,
        created_by=ops_user,
        booking_date=datetime.date(2024, 5, 1),
        booking_validity_date=datetime.date(2024, 5, 31),
        forwarding_window_start=datetime.date(2024, 5, 10),
        forwarding_window_end=datetime.date(2024, 5, 20),
        shipping_line=master_data['shipping_line'],
        pol=master_data['pol'],
        pod=master_data['pod'],
        client=master_data['client'],
        commodity=master_data['commodity'],
        cargo_type=Booking.CargoType.FCL,
        shipment_type='Direct',
        stuffing_type='Factory',
    )
    booking.save()
    return booking


@pytest.fixture
def ops_client(ops_user):
    """Return an API client authenticated as an Operations user."""
    client = APIClient()
    client.force_authenticate(user=ops_user)
    return client


@pytest.fixture
def sales_client(sales_user):
    """Return an API client authenticated as a Sales user."""
    client = APIClient()
    client.force_authenticate(user=sales_user)
    return client


@pytest.fixture
def admin_client(admin_user):
    """Return an API client authenticated as an Admin user."""
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


class TestBookingUpdateSuccess:
    """Tests for successful booking updates (Requirement 3.1, 3.3)."""

    def test_update_booking_voyage(self, ops_client, pending_booking):
        """PUT update changes a field and returns updated booking."""
        url = f'/api/bookings/{pending_booking.pk}/'
        response = ops_client.put(url, {'voyage': 'V123-WEST'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['voyage'] == 'V123-WEST'

    def test_partial_update_booking(self, ops_client, pending_booking):
        """PATCH partial update changes a field."""
        url = f'/api/bookings/{pending_booking.pk}/'
        response = ops_client.patch(url, {'buyer': 'ACME Corp'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['buyer'] == 'ACME Corp'

    def test_update_records_updated_by(self, ops_client, ops_user, pending_booking):
        """Successful update records updated_by user (Requirement 3.3)."""
        url = f'/api/bookings/{pending_booking.pk}/'
        response = ops_client.put(url, {'voyage': 'V999'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['updated_by'] == ops_user.pk

    def test_update_records_updated_at(self, ops_client, pending_booking):
        """Successful update records updated_at timestamp (Requirement 3.3)."""
        url = f'/api/bookings/{pending_booking.pk}/'
        response = ops_client.put(url, {'voyage': 'V999'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['updated_at'] is not None

    def test_admin_can_update_booking(self, admin_client, pending_booking):
        """Admin user can also update bookings (Requirement 3.5)."""
        url = f'/api/bookings/{pending_booking.pk}/'
        response = admin_client.put(url, {'voyage': 'ADMIN-V1'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['voyage'] == 'ADMIN-V1'


class TestBookingUpdateRejectedCompleted:
    """Tests for rejection of updates to completed bookings (Requirement 3.2)."""

    def test_update_completed_booking_rejected(self, ops_client, completed_booking):
        """Cannot update a completed booking."""
        url = f'/api/bookings/{completed_booking.pk}/'
        response = ops_client.put(url, {'voyage': 'NEW-VOYAGE'})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'finalized' in str(response.data).lower() or 'completed' in str(response.data).lower()

    def test_completed_booking_data_unchanged(self, ops_client, completed_booking):
        """Completed booking data remains unchanged after failed update."""
        original_voyage = completed_booking.voyage
        url = f'/api/bookings/{completed_booking.pk}/'
        ops_client.put(url, {'voyage': 'SHOULD-NOT-CHANGE'})
        completed_booking.refresh_from_db()
        assert completed_booking.voyage == original_voyage


class TestBookingUpdateNotFound:
    """Tests for 404 on non-existent bookings (Requirement 3.4)."""

    def test_update_nonexistent_booking_returns_404(self, ops_client):
        """Attempting to update a non-existent booking returns 404."""
        url = '/api/bookings/99999/'
        response = ops_client.put(url, {'voyage': 'V123'})
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestBookingUpdatePermissions:
    """Tests for permission enforcement (Requirement 3.5)."""

    def test_sales_user_cannot_update_booking(self, sales_client, pending_booking):
        """Sales user is rejected from updating bookings."""
        url = f'/api/bookings/{pending_booking.pk}/'
        response = sales_client.put(url, {'voyage': 'V123'})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_user_cannot_update(self, pending_booking):
        """Unauthenticated user is rejected."""
        client = APIClient()
        url = f'/api/bookings/{pending_booking.pk}/'
        response = client.put(url, {'voyage': 'V123'})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestBookingUpdateValidation:
    """Tests for validation on update (Requirement 3.1)."""

    def test_update_with_invalid_date_ordering(self, ops_client, pending_booking):
        """Update with booking_validity_date before booking_date is rejected."""
        url = f'/api/bookings/{pending_booking.pk}/'
        response = ops_client.put(url, {
            'booking_date': '2024-06-15',
            'booking_validity_date': '2024-06-01',
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'booking_validity_date' in response.data

    def test_update_with_invalid_forwarding_window(self, ops_client, pending_booking):
        """Update with forwarding_window_end before start is rejected."""
        url = f'/api/bookings/{pending_booking.pk}/'
        response = ops_client.put(url, {
            'forwarding_window_start': '2024-06-20',
            'forwarding_window_end': '2024-06-10',
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'forwarding_window_end' in response.data

    def test_update_haz_true_without_required_fields(self, ops_client, pending_booking):
        """Setting is_haz=True without haz_class/uin/group is rejected."""
        url = f'/api/bookings/{pending_booking.pk}/'
        response = ops_client.put(url, {'is_haz': True})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
