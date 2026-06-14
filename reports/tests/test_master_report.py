"""
Tests for the Master Report endpoint.
"""

import datetime

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from bookings.models import Booking, Container
from master_data.models import (
    Client,
    Commodity,
    ContainerType,
    Port,
    ShippingLine,
    Vessel,
)

User = get_user_model()

MASTER_URL = '/api/reports/master/'


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
    """Create required master data for bookings."""
    shipping_line = ShippingLine.objects.create(name='Maersk', code='MAEU')
    shipping_line_2 = ShippingLine.objects.create(name='MSC', code='MSCU')
    pol = Port.objects.create(name='Mumbai Port', code='INMUN', country='India')
    pod = Port.objects.create(name='Rotterdam Port', code='NLRTM', country='Netherlands')
    client = Client.objects.create(name='Test Client', email='client@test.com')
    client_2 = Client.objects.create(name='Another Client', email='client2@test.com')
    commodity = Commodity.objects.create(name='Electronics', hs_code='8542')
    container_type = ContainerType.objects.create(name='Standard', code='GP')
    vessel = Vessel.objects.create(name='Ever Given', shipping_line=shipping_line)
    return {
        'shipping_line': shipping_line,
        'shipping_line_2': shipping_line_2,
        'pol': pol,
        'pod': pod,
        'client': client,
        'client_2': client_2,
        'commodity': commodity,
        'container_type': container_type,
        'vessel': vessel,
    }


@pytest.fixture
def api_client():
    return APIClient()


def _create_booking(master_data, ops_user, **overrides):
    """Helper to create a booking with defaults."""
    today = timezone.now().date()
    defaults = {
        'booking_date': today - datetime.timedelta(days=5),
        'booking_validity_date': today + datetime.timedelta(days=10),
        'forwarding_window_start': today + datetime.timedelta(days=1),
        'forwarding_window_end': today + datetime.timedelta(days=7),
        'shipping_line': master_data['shipping_line'],
        'pol': master_data['pol'],
        'pod': master_data['pod'],
        'client': master_data['client'],
        'commodity': master_data['commodity'],
        'cargo_type': 'FCL',
        'shipment_type': 'Direct',
        'stuffing_type': 'Factory',
        'status': Booking.Status.PENDING,
        'created_by': ops_user,
    }
    defaults.update(overrides)
    return Booking.objects.create(**defaults)


class TestMasterReportAllStatuses:
    """Tests that Master report includes all bookings regardless of status."""

    def test_includes_all_statuses(self, api_client, ops_user, master_data):
        """All bookings appear regardless of status."""
        api_client.force_authenticate(user=ops_user)

        pending = _create_booking(master_data, ops_user, status=Booking.Status.PENDING)
        do_edit = _create_booking(
            master_data, ops_user, status=Booking.Status.DO_BOOKING_EDIT
        )
        completed = _create_booking(
            master_data, ops_user, status=Booking.Status.COMPLETED
        )

        response = api_client.get(MASTER_URL)

        assert response.status_code == status.HTTP_200_OK
        references = [r['booking_reference'] for r in response.data['results']]
        assert pending.job_number in references
        assert do_edit.job_number in references
        assert completed.job_number in references


class TestMasterReportFiltering:
    """Tests for Master report filtering."""

    def test_filter_by_client(self, api_client, ops_user, master_data):
        """Filtering by client ID returns only that client's bookings."""
        api_client.force_authenticate(user=ops_user)

        b1 = _create_booking(master_data, ops_user, client=master_data['client'])
        b2 = _create_booking(master_data, ops_user, client=master_data['client_2'])

        response = api_client.get(MASTER_URL, {'client': master_data['client'].pk})

        assert response.status_code == status.HTTP_200_OK
        references = [r['booking_reference'] for r in response.data['results']]
        assert b1.job_number in references
        assert b2.job_number not in references

    def test_filter_by_shipping_line(self, api_client, ops_user, master_data):
        """Filtering by shipping line returns only matching bookings."""
        api_client.force_authenticate(user=ops_user)

        b1 = _create_booking(
            master_data, ops_user, shipping_line=master_data['shipping_line']
        )
        b2 = _create_booking(
            master_data, ops_user, shipping_line=master_data['shipping_line_2']
        )

        response = api_client.get(
            MASTER_URL, {'shipping_line': master_data['shipping_line'].pk}
        )

        assert response.status_code == status.HTTP_200_OK
        references = [r['booking_reference'] for r in response.data['results']]
        assert b1.job_number in references
        assert b2.job_number not in references

    def test_filter_by_vessel_voyage(self, api_client, ops_user, master_data):
        """Filtering by vessel_voyage searches vessel name and voyage field."""
        api_client.force_authenticate(user=ops_user)

        b1 = _create_booking(
            master_data, ops_user, vessel=master_data['vessel'], voyage='V123'
        )
        b2 = _create_booking(master_data, ops_user, vessel=None, voyage='X999')

        response = api_client.get(MASTER_URL, {'vessel_voyage': 'Ever'})

        assert response.status_code == status.HTTP_200_OK
        references = [r['booking_reference'] for r in response.data['results']]
        assert b1.job_number in references
        assert b2.job_number not in references

    def test_filter_by_status(self, api_client, ops_user, master_data):
        """Filtering by status returns only bookings with that status."""
        api_client.force_authenticate(user=ops_user)

        pending = _create_booking(master_data, ops_user, status=Booking.Status.PENDING)
        completed = _create_booking(
            master_data, ops_user, status=Booking.Status.COMPLETED
        )

        response = api_client.get(MASTER_URL, {'status': 'COMPLETED'})

        assert response.status_code == status.HTTP_200_OK
        references = [r['booking_reference'] for r in response.data['results']]
        assert completed.job_number in references
        assert pending.job_number not in references

    def test_default_last_90_days(self, api_client, ops_user, master_data):
        """Without date range, only bookings from last 90 days are returned."""
        api_client.force_authenticate(user=ops_user)

        # Recent booking - created within 90 days (now)
        recent = _create_booking(master_data, ops_user)

        # Old booking - manually set created_at to > 90 days ago
        old = _create_booking(master_data, ops_user)
        old_date = timezone.now() - datetime.timedelta(days=100)
        Booking.objects.filter(pk=old.pk).update(created_at=old_date)

        response = api_client.get(MASTER_URL)

        assert response.status_code == status.HTTP_200_OK
        references = [r['booking_reference'] for r in response.data['results']]
        assert recent.job_number in references
        assert old.job_number not in references

    def test_custom_date_range(self, api_client, ops_user, master_data):
        """Custom created date range filters bookings within that range."""
        api_client.force_authenticate(user=ops_user)

        b1 = _create_booking(master_data, ops_user)
        b2 = _create_booking(master_data, ops_user)

        # Set created_at to specific dates
        Booking.objects.filter(pk=b1.pk).update(
            created_at=timezone.make_aware(datetime.datetime(2024, 3, 15, 12, 0, 0))
        )
        Booking.objects.filter(pk=b2.pk).update(
            created_at=timezone.make_aware(datetime.datetime(2024, 1, 10, 12, 0, 0))
        )

        response = api_client.get(
            MASTER_URL,
            {'created_date_from': '2024-02-01', 'created_date_to': '2024-03-31'},
        )

        assert response.status_code == status.HTTP_200_OK
        references = [r['booking_reference'] for r in response.data['results']]
        assert b1.job_number in references
        assert b2.job_number not in references


class TestMasterReportSorting:
    """Tests for Master report sorting."""

    def test_sorted_by_created_date_descending(self, api_client, ops_user, master_data):
        """Results are ordered by created_at descending (newest first)."""
        api_client.force_authenticate(user=ops_user)

        import time

        b_first = _create_booking(master_data, ops_user)
        time.sleep(0.01)
        b_second = _create_booking(master_data, ops_user)
        time.sleep(0.01)
        b_third = _create_booking(master_data, ops_user)

        response = api_client.get(MASTER_URL)

        assert response.status_code == status.HTTP_200_OK
        references = [r['booking_reference'] for r in response.data['results']]
        # Descending: newest first
        assert references == [
            b_third.job_number,
            b_second.job_number,
            b_first.job_number,
        ]


class TestMasterReportResponse:
    """Tests for Master report response structure."""

    def test_empty_results_message(self, api_client, ops_user, master_data):
        """Empty queryset returns a message indicating no results."""
        api_client.force_authenticate(user=ops_user)

        response = api_client.get(MASTER_URL)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['results'] == []
        assert 'message' in response.data

    def test_response_contains_expected_fields(
        self, api_client, ops_user, master_data
    ):
        """Response items contain all required columns."""
        api_client.force_authenticate(user=ops_user)

        booking = _create_booking(
            master_data,
            ops_user,
            vessel=master_data['vessel'],
            voyage='V100',
        )
        Container.objects.create(
            booking=booking,
            container_type=master_data['container_type'],
            container_size='20FT',
            container_count=3,
        )

        response = api_client.get(MASTER_URL)

        assert response.status_code == status.HTTP_200_OK
        item = response.data['results'][0]
        assert item['booking_reference'] == booking.job_number
        assert item['client_name'] == 'Test Client'
        assert 'Ever Given' in item['vessel_voyage']
        assert 'V100' in item['vessel_voyage']
        assert item['pol'] == 'Mumbai Port'
        assert item['pod'] == 'Rotterdam Port'
        assert item['status_display'] == 'Pending'
        assert item['shipping_line'] == 'Maersk'
        assert item['container_count'] == 3
        assert item['created_date'] is not None

    def test_container_count_sums_multiple_containers(
        self, api_client, ops_user, master_data
    ):
        """Container count sums across all containers on the booking."""
        api_client.force_authenticate(user=ops_user)

        booking = _create_booking(master_data, ops_user)
        Container.objects.create(
            booking=booking,
            container_type=master_data['container_type'],
            container_size='20FT',
            container_count=2,
        )
        Container.objects.create(
            booking=booking,
            container_type=master_data['container_type'],
            container_size='40FT',
            container_count=1,
        )

        response = api_client.get(MASTER_URL)

        assert response.status_code == status.HTTP_200_OK
        item = response.data['results'][0]
        assert item['container_count'] == 3


class TestMasterReportPagination:
    """Tests for pagination of the Master report."""

    def test_max_50_per_page(self, api_client, ops_user, master_data):
        """Report is paginated with max 50 items per page."""
        api_client.force_authenticate(user=ops_user)

        # Create 55 bookings
        for i in range(55):
            _create_booking(master_data, ops_user)

        response = api_client.get(MASTER_URL)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 50
        assert response.data['count'] == 55
        assert response.data['next'] is not None

    def test_second_page(self, api_client, ops_user, master_data):
        """Second page returns remaining items."""
        api_client.force_authenticate(user=ops_user)

        for i in range(55):
            _create_booking(master_data, ops_user)

        response = api_client.get(MASTER_URL, {'page': 2})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 5


class TestMasterReportPermissions:
    """Tests for permission enforcement on the Master report."""

    def test_unauthenticated_denied(self, api_client):
        """Unauthenticated requests are denied."""
        response = api_client.get(MASTER_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_sales_user_denied(self, api_client, sales_user):
        """Sales users cannot access the report."""
        api_client.force_authenticate(user=sales_user)
        response = api_client.get(MASTER_URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_ops_user_allowed(self, api_client, ops_user):
        """Operations users can access the report."""
        api_client.force_authenticate(user=ops_user)
        response = api_client.get(MASTER_URL)
        assert response.status_code == status.HTTP_200_OK

    def test_admin_user_allowed(self, api_client, admin_user):
        """Admin users can access the report."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.get(MASTER_URL)
        assert response.status_code == status.HTTP_200_OK
