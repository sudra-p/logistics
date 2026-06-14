"""
Tests for the booking search endpoint (GET /api/bookings/search/).
Covers: filtering, quick search, AND logic, pagination, sorting, validation.
"""

import datetime

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
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

SEARCH_URL = '/api/bookings/search/'


@pytest.fixture
def ops_user(db):
    """Create an Operations group user."""
    user = User.objects.create_user(username='ops_search', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Operations')
    user.groups.add(group)
    return user


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def master_data(db):
    """Create required master data for booking creation."""
    shipping_line = ShippingLine.objects.create(name='Maersk', code='MAEU')
    pol = Port.objects.create(name='Mumbai Port', code='INMUN', country='India')
    pod = Port.objects.create(name='Rotterdam Port', code='NLRTM', country='Netherlands')
    client = Client.objects.create(name='Test Client', email='client@test.com')
    client2 = Client.objects.create(name='Second Client', email='client2@test.com')
    commodity = Commodity.objects.create(name='Electronics', hs_code='8542')
    container_type = ContainerType.objects.create(name='Standard', code='STD')
    return {
        'shipping_line': shipping_line,
        'pol': pol,
        'pod': pod,
        'client': client,
        'client2': client2,
        'commodity': commodity,
        'container_type': container_type,
    }


def _create_booking(ops_user, master_data, **overrides):
    """Helper to create a booking directly via model for test setup."""
    defaults = {
        'booking_date': datetime.date(2024, 3, 1),
        'booking_validity_date': datetime.date(2024, 3, 15),
        'forwarding_window_start': datetime.date(2024, 3, 5),
        'forwarding_window_end': datetime.date(2024, 3, 10),
        'shipping_line': master_data['shipping_line'],
        'pol': master_data['pol'],
        'pod': master_data['pod'],
        'client': master_data['client'],
        'commodity': master_data['commodity'],
        'cargo_type': 'FCL',
        'shipment_type': 'Direct',
        'stuffing_type': 'Factory',
        'created_by': ops_user,
    }
    defaults.update(overrides)
    return Booking.objects.create(**defaults)


class TestSearchFilterByClient:
    """Test filtering bookings by client ID."""

    def test_filter_by_client(self, api_client, ops_user, master_data):
        b1 = _create_booking(ops_user, master_data, client=master_data['client'])
        _create_booking(ops_user, master_data, client=master_data['client2'])

        api_client.force_authenticate(user=ops_user)
        response = api_client.get(SEARCH_URL, {'client': master_data['client'].pk})

        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        assert len(results) == 1
        assert results[0]['id'] == b1.pk


class TestSearchFilterByStatus:
    """Test filtering bookings by status."""

    def test_filter_by_status(self, api_client, ops_user, master_data):
        _create_booking(ops_user, master_data, status='PENDING')
        b2 = _create_booking(ops_user, master_data, status='COMPLETED')

        api_client.force_authenticate(user=ops_user)
        response = api_client.get(SEARCH_URL, {'status': 'COMPLETED'})

        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        assert len(results) == 1
        assert results[0]['id'] == b2.pk


class TestSearchFilterByDateRange:
    """Test filtering bookings by booking date range."""

    def test_filter_by_date_range(self, api_client, ops_user, master_data):
        b1 = _create_booking(
            ops_user, master_data,
            booking_date=datetime.date(2024, 3, 1),
            booking_validity_date=datetime.date(2024, 3, 15),
        )
        _create_booking(
            ops_user, master_data,
            booking_date=datetime.date(2024, 4, 15),
            booking_validity_date=datetime.date(2024, 4, 30),
        )

        api_client.force_authenticate(user=ops_user)
        response = api_client.get(SEARCH_URL, {
            'booking_date_from': '2024-02-01',
            'booking_date_to': '2024-03-31',
        })

        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        assert len(results) == 1
        assert results[0]['id'] == b1.pk


class TestQuickSearchByJobNumber:
    """Test quick search (q param) for exact match on job_number."""

    def test_quick_search_job_number(self, api_client, ops_user, master_data):
        b1 = _create_booking(ops_user, master_data)
        _create_booking(ops_user, master_data)

        api_client.force_authenticate(user=ops_user)
        response = api_client.get(SEARCH_URL, {'q': b1.job_number})

        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        assert len(results) == 1
        assert results[0]['job_number'] == b1.job_number


class TestQuickSearchByContainerNo:
    """Test container_no filter for exact match on related Container."""

    def test_search_by_container_no(self, api_client, ops_user, master_data):
        b1 = _create_booking(ops_user, master_data)
        _create_booking(ops_user, master_data)

        Container.objects.create(
            booking=b1,
            container_type=master_data['container_type'],
            container_size='20FT',
            container_count=1,
            container_no='MSKU1234567',
        )

        api_client.force_authenticate(user=ops_user)
        response = api_client.get(SEARCH_URL, {'container_no': 'MSKU1234567'})

        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        assert len(results) == 1
        assert results[0]['id'] == b1.pk


class TestCombinedFiltersANDLogic:
    """Test that multiple filters combine with AND logic."""

    def test_combined_filters(self, api_client, ops_user, master_data):
        # Matches both: client=client, status=PENDING
        b1 = _create_booking(
            ops_user, master_data,
            client=master_data['client'],
            status='PENDING',
        )
        # Matches client but not status
        _create_booking(
            ops_user, master_data,
            client=master_data['client'],
            status='COMPLETED',
        )
        # Matches status but not client
        _create_booking(
            ops_user, master_data,
            client=master_data['client2'],
            status='PENDING',
        )

        api_client.force_authenticate(user=ops_user)
        response = api_client.get(SEARCH_URL, {
            'client': master_data['client'].pk,
            'status': 'PENDING',
        })

        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        assert len(results) == 1
        assert results[0]['id'] == b1.pk


class TestEmptyResults:
    """Test that empty results return count=0."""

    def test_empty_results(self, api_client, ops_user, master_data):
        _create_booking(ops_user, master_data)

        api_client.force_authenticate(user=ops_user)
        response = api_client.get(SEARCH_URL, {'q': 'NONEXISTENT-JOB'})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0
        assert response.data['results'] == []


class TestPagination:
    """Test paginated response structure."""

    def test_paginated_response(self, api_client, ops_user, master_data):
        # Create 30 bookings to exceed default page size of 25
        for i in range(30):
            _create_booking(
                ops_user, master_data,
                booking_date=datetime.date(2024, 3, 1) + datetime.timedelta(days=i),
                booking_validity_date=datetime.date(2024, 4, 1) + datetime.timedelta(days=i),
            )

        api_client.force_authenticate(user=ops_user)
        response = api_client.get(SEARCH_URL)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 30
        assert len(response.data['results']) == 25  # Default page size
        assert response.data['next'] is not None
        assert response.data['previous'] is None


class TestInvalidDateRangeRejected:
    """Test that invalid date ranges (from > to) are rejected."""

    def test_invalid_booking_date_range(self, api_client, ops_user, master_data):
        api_client.force_authenticate(user=ops_user)
        response = api_client.get(SEARCH_URL, {
            'booking_date_from': '2024-04-01',
            'booking_date_to': '2024-03-01',
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'detail' in response.data

    def test_invalid_etd_range(self, api_client, ops_user, master_data):
        api_client.force_authenticate(user=ops_user)
        response = api_client.get(SEARCH_URL, {
            'etd_from': '2024-04-01T00:00:00Z',
            'etd_to': '2024-03-01T00:00:00Z',
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'detail' in response.data


class TestDefaultSortByBookingDateDesc:
    """Test default sorting by booking_date descending."""

    def test_default_sort(self, api_client, ops_user, master_data):
        b_old = _create_booking(
            ops_user, master_data,
            booking_date=datetime.date(2024, 1, 1),
            booking_validity_date=datetime.date(2024, 1, 15),
        )
        b_new = _create_booking(
            ops_user, master_data,
            booking_date=datetime.date(2024, 6, 1),
            booking_validity_date=datetime.date(2024, 6, 15),
        )

        api_client.force_authenticate(user=ops_user)
        response = api_client.get(SEARCH_URL)

        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        assert len(results) == 2
        assert results[0]['id'] == b_new.pk
        assert results[1]['id'] == b_old.pk
