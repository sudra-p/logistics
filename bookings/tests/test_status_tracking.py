"""
Tests for booking status transition logic and endpoints.
Validates Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APIClient

from bookings.models import Booking, BookingStatusHistory
from master_data.models import Client, Commodity, Port, ShippingLine

User = get_user_model()


@pytest.fixture
def ops_user(db):
    """Create an Operations group user."""
    user = User.objects.create_user(username='ops_status', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Operations')
    user.groups.add(group)
    return user


@pytest.fixture
def sales_user(db):
    """Create a Sales group user (no modify permission)."""
    user = User.objects.create_user(username='sales_status', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Sales')
    user.groups.add(group)
    return user


@pytest.fixture
def master_data(db):
    """Create required master data for booking creation."""
    shipping_line = ShippingLine.objects.create(name='Maersk Status', code='MAES')
    pol = Port.objects.create(name='Mumbai Status', code='INMUS', country='India')
    pod = Port.objects.create(name='Rotterdam Status', code='NLRTS', country='Netherlands')
    client = Client.objects.create(name='Status Client', email='statusclient@test.com')
    commodity = Commodity.objects.create(name='Electronics Status', hs_code='8543')
    return {
        'shipping_line': shipping_line,
        'pol': pol,
        'pod': pod,
        'client': client,
        'commodity': commodity,
    }


@pytest.fixture
def booking_pending(ops_user, master_data):
    """Create a booking in PENDING status with all mandatory fields."""
    booking = Booking(
        status=Booking.Status.PENDING,
        booking_date='2024-03-01',
        booking_validity_date='2024-03-15',
        forwarding_window_start='2024-03-05',
        forwarding_window_end='2024-03-10',
        shipping_line=master_data['shipping_line'],
        pol=master_data['pol'],
        pod=master_data['pod'],
        client=master_data['client'],
        commodity=master_data['commodity'],
        cargo_type='FCL',
        shipment_type='Direct',
        stuffing_type='Factory',
        created_by=ops_user,
    )
    booking.save()
    return booking


@pytest.fixture
def booking_do_edit(ops_user, master_data):
    """Create a booking in DO_BOOKING_EDIT status with all mandatory fields."""
    booking = Booking(
        status=Booking.Status.DO_BOOKING_EDIT,
        booking_date='2024-03-01',
        booking_validity_date='2024-03-15',
        forwarding_window_start='2024-03-05',
        forwarding_window_end='2024-03-10',
        shipping_line=master_data['shipping_line'],
        pol=master_data['pol'],
        pod=master_data['pod'],
        client=master_data['client'],
        commodity=master_data['commodity'],
        cargo_type='FCL',
        shipment_type='Direct',
        stuffing_type='Factory',
        created_by=ops_user,
    )
    booking.save()
    return booking


@pytest.fixture
def booking_completed(ops_user, master_data):
    """Create a booking in COMPLETED status."""
    booking = Booking(
        status=Booking.Status.COMPLETED,
        booking_date='2024-03-01',
        booking_validity_date='2024-03-15',
        forwarding_window_start='2024-03-05',
        forwarding_window_end='2024-03-10',
        shipping_line=master_data['shipping_line'],
        pol=master_data['pol'],
        pod=master_data['pod'],
        client=master_data['client'],
        commodity=master_data['commodity'],
        cargo_type='FCL',
        shipment_type='Direct',
        stuffing_type='Factory',
        created_by=ops_user,
    )
    booking.save()
    return booking


@pytest.fixture
def api_client():
    return APIClient()


class TestValidStatusTransitions:
    """Tests for valid status transitions (Req 7.1)."""

    def test_pending_to_do_booking_edit(self, api_client, ops_user, booking_pending):
        """Valid transition: PENDING → DO_BOOKING_EDIT."""
        api_client.force_authenticate(user=ops_user)
        response = api_client.patch(
            f'/api/bookings/{booking_pending.pk}/status/',
            {'status': 'DO_BOOKING_EDIT'},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'DO_BOOKING_EDIT'

        # Verify in DB
        booking_pending.refresh_from_db()
        assert booking_pending.status == Booking.Status.DO_BOOKING_EDIT

    def test_do_booking_edit_to_completed(self, api_client, ops_user, booking_do_edit):
        """Valid transition: DO_BOOKING_EDIT → COMPLETED with all mandatory fields."""
        api_client.force_authenticate(user=ops_user)
        response = api_client.patch(
            f'/api/bookings/{booking_do_edit.pk}/status/',
            {'status': 'COMPLETED'},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'COMPLETED'

        # Verify in DB
        booking_do_edit.refresh_from_db()
        assert booking_do_edit.status == Booking.Status.COMPLETED


class TestInvalidStatusTransitions:
    """Tests for invalid status transitions (Req 7.5)."""

    def test_pending_to_completed_rejected(self, api_client, ops_user, booking_pending):
        """Reject skipping: PENDING → COMPLETED directly."""
        api_client.force_authenticate(user=ops_user)
        response = api_client.patch(
            f'/api/bookings/{booking_pending.pk}/status/',
            {'status': 'COMPLETED'},
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'status' in response.data

        # Status unchanged
        booking_pending.refresh_from_db()
        assert booking_pending.status == Booking.Status.PENDING

    def test_completed_to_anything_rejected(self, api_client, ops_user, booking_completed):
        """Reject backwards: COMPLETED → any state."""
        api_client.force_authenticate(user=ops_user)

        # Try to go back to DO_BOOKING_EDIT
        response = api_client.patch(
            f'/api/bookings/{booking_completed.pk}/status/',
            {'status': 'DO_BOOKING_EDIT'},
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'status' in response.data
        assert 'terminal' in response.data['status'].lower()

        # Try to go back to PENDING
        response = api_client.patch(
            f'/api/bookings/{booking_completed.pk}/status/',
            {'status': 'PENDING'},
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_do_booking_edit_to_pending_rejected(self, api_client, ops_user, booking_do_edit):
        """Reject backwards: DO_BOOKING_EDIT → PENDING."""
        api_client.force_authenticate(user=ops_user)
        response = api_client.patch(
            f'/api/bookings/{booking_do_edit.pk}/status/',
            {'status': 'PENDING'},
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'status' in response.data

        # Status unchanged
        booking_do_edit.refresh_from_db()
        assert booking_do_edit.status == Booking.Status.DO_BOOKING_EDIT


class TestCompletedMandatoryFieldValidation:
    """Tests for mandatory field validation on COMPLETED transition (Req 7.3, 7.4)."""

    def test_missing_mandatory_fields_on_completed(self, api_client, ops_user, master_data):
        """Reject COMPLETED if mandatory fields are missing."""
        # Create a booking with missing shipment_type and stuffing_type
        booking = Booking(
            status=Booking.Status.DO_BOOKING_EDIT,
            booking_date='2024-03-01',
            booking_validity_date='2024-03-15',
            forwarding_window_start='2024-03-05',
            forwarding_window_end='2024-03-10',
            shipping_line=master_data['shipping_line'],
            pol=master_data['pol'],
            pod=master_data['pod'],
            client=master_data['client'],
            commodity=master_data['commodity'],
            cargo_type='FCL',
            shipment_type='',  # Empty mandatory field
            stuffing_type='',  # Empty mandatory field
            created_by=ops_user,
        )
        booking.save()

        api_client.force_authenticate(user=ops_user)
        response = api_client.patch(
            f'/api/bookings/{booking.pk}/status/',
            {'status': 'COMPLETED'},
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'status' in response.data
        assert 'shipment_type' in response.data['status']
        assert 'stuffing_type' in response.data['status']

        # Status unchanged
        booking.refresh_from_db()
        assert booking.status == Booking.Status.DO_BOOKING_EDIT


class TestStatusHistory:
    """Tests for status history recording (Req 7.6)."""

    def test_history_created_on_transition(self, api_client, ops_user, booking_pending):
        """BookingStatusHistory record created on each successful transition."""
        api_client.force_authenticate(user=ops_user)
        api_client.patch(
            f'/api/bookings/{booking_pending.pk}/status/',
            {'status': 'DO_BOOKING_EDIT'},
            format='json',
        )

        history = BookingStatusHistory.objects.filter(booking=booking_pending)
        assert history.count() == 1

        record = history.first()
        assert record.previous_status == Booking.Status.PENDING
        assert record.new_status == Booking.Status.DO_BOOKING_EDIT
        assert record.changed_by == ops_user

    def test_multiple_transitions_create_multiple_history(
        self, api_client, ops_user, booking_pending
    ):
        """Multiple transitions create multiple history records."""
        api_client.force_authenticate(user=ops_user)

        # First transition
        api_client.patch(
            f'/api/bookings/{booking_pending.pk}/status/',
            {'status': 'DO_BOOKING_EDIT'},
            format='json',
        )
        # Second transition
        api_client.patch(
            f'/api/bookings/{booking_pending.pk}/status/',
            {'status': 'COMPLETED'},
            format='json',
        )

        history = BookingStatusHistory.objects.filter(booking=booking_pending)
        assert history.count() == 2

    def test_history_endpoint_returns_records(self, api_client, ops_user, booking_pending):
        """GET /api/bookings/{id}/history/ returns status history records."""
        api_client.force_authenticate(user=ops_user)

        # Make a transition first
        api_client.patch(
            f'/api/bookings/{booking_pending.pk}/status/',
            {'status': 'DO_BOOKING_EDIT'},
            format='json',
        )

        # Query history
        response = api_client.get(
            f'/api/bookings/{booking_pending.pk}/history/',
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['previous_status'] == 'PENDING'
        assert response.data[0]['new_status'] == 'DO_BOOKING_EDIT'
        assert response.data[0]['changed_by'] == ops_user.pk

    def test_no_history_for_failed_transition(self, api_client, ops_user, booking_pending):
        """No history record created when transition is rejected."""
        api_client.force_authenticate(user=ops_user)
        api_client.patch(
            f'/api/bookings/{booking_pending.pk}/status/',
            {'status': 'COMPLETED'},  # Invalid: skip from PENDING
            format='json',
        )

        history = BookingStatusHistory.objects.filter(booking=booking_pending)
        assert history.count() == 0


class TestStatusPermissions:
    """Tests for permission enforcement on status endpoints."""

    def test_sales_user_cannot_change_status(
        self, api_client, sales_user, booking_pending
    ):
        """Sales user (no CanModifyBooking) cannot change booking status."""
        api_client.force_authenticate(user=sales_user)
        response = api_client.patch(
            f'/api/bookings/{booking_pending.pk}/status/',
            {'status': 'DO_BOOKING_EDIT'},
            format='json',
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_sales_user_can_view_history(
        self, api_client, sales_user, ops_user, booking_pending
    ):
        """Sales user (CanViewBooking) can view status history for their bookings."""
        from master_data.models import MarketingPerson

        # Link booking to sales user via marketing person
        mp = MarketingPerson.objects.create(name='Sales MP', user=sales_user)
        booking_pending.marketing_person = mp
        booking_pending.save()

        # Create history as ops user first
        ops_client = APIClient()
        ops_client.force_authenticate(user=ops_user)
        ops_client.patch(
            f'/api/bookings/{booking_pending.pk}/status/',
            {'status': 'DO_BOOKING_EDIT'},
            format='json',
        )

        # Sales user can read history
        api_client.force_authenticate(user=sales_user)
        response = api_client.get(
            f'/api/bookings/{booking_pending.pk}/history/',
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    def test_unauthenticated_user_denied(self, api_client, booking_pending):
        """Unauthenticated request returns 401."""
        response = api_client.patch(
            f'/api/bookings/{booking_pending.pk}/status/',
            {'status': 'DO_BOOKING_EDIT'},
            format='json',
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
