"""
Tests for the Operations Tracking View API endpoint.
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

OPERATIONS_URL = '/api/operations/'


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
    """Create a Sales group user (should be denied access)."""
    user = User.objects.create_user(username='sales_user', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Sales')
    user.groups.add(group)
    return user


@pytest.fixture
def accounts_user(db):
    """Create an Accounts group user (should be denied access)."""
    user = User.objects.create_user(username='accounts_user', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Accounts')
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
def sample_booking(master_data, ops_user):
    """Create a sample booking for testing."""
    return Booking.objects.create(
        booking_date=datetime.date(2024, 3, 1),
        booking_validity_date=datetime.date(2024, 3, 15),
        forwarding_window_start=datetime.date(2024, 3, 5),
        forwarding_window_end=datetime.date(2024, 3, 10),
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


class TestOperationsViewPermissions:
    """Test that only Operations and Admin users can access the operations view."""

    def test_operations_user_can_access(self, ops_user, sample_booking):
        client = APIClient()
        client.force_authenticate(user=ops_user)
        response = client.get(OPERATIONS_URL)
        assert response.status_code == status.HTTP_200_OK

    def test_admin_user_can_access(self, admin_user, sample_booking):
        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get(OPERATIONS_URL)
        assert response.status_code == status.HTTP_200_OK

    def test_sales_user_denied(self, sales_user):
        client = APIClient()
        client.force_authenticate(user=sales_user)
        response = client.get(OPERATIONS_URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_accounts_user_denied(self, accounts_user):
        client = APIClient()
        client.force_authenticate(user=accounts_user)
        response = client.get(OPERATIONS_URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_user_denied(self):
        client = APIClient()
        response = client.get(OPERATIONS_URL)
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


class TestOperationsViewResponse:
    """Test the operations view returns expected data structure."""

    def test_returns_paginated_results(self, ops_user, sample_booking):
        client = APIClient()
        client.force_authenticate(user=ops_user)
        response = client.get(OPERATIONS_URL)
        assert response.status_code == status.HTTP_200_OK
        # Paginated response should have count, next, previous, results
        assert 'count' in response.data
        assert 'results' in response.data
        assert response.data['count'] == 1

    def test_returns_booking_data(self, ops_user, sample_booking):
        client = APIClient()
        client.force_authenticate(user=ops_user)
        response = client.get(OPERATIONS_URL)
        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        assert len(results) == 1
        booking_data = results[0]
        # Verify all required fields are present
        assert booking_data['booking_number'] == sample_booking.job_number
        assert booking_data['shipping_line'] == 'Maersk'
        assert booking_data['pol'] == 'Mumbai Port'
        assert booking_data['pod'] == 'Rotterdam Port'
        # Nullable fields should be None when not set
        assert booking_data['pi_number'] is None
        assert booking_data['consignee'] is None
        assert booking_data['container_type'] is None
        assert booking_data['vessel_name'] is None
        assert booking_data['voyage'] == ''
        assert booking_data['fpd'] is None
        assert booking_data['etd'] is None
        assert booking_data['eta'] is None
        assert booking_data['forwarder'] is None

    def test_empty_results_when_no_bookings(self, ops_user):
        client = APIClient()
        client.force_authenticate(user=ops_user)
        response = client.get(OPERATIONS_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0
        assert response.data['results'] == []

    def test_pagination_defaults_to_25(self, ops_user, master_data):
        """Verify that pagination uses page_size=25 by default."""
        # Create 30 bookings
        for i in range(30):
            Booking.objects.create(
                booking_date=datetime.date(2024, 3, 1),
                booking_validity_date=datetime.date(2024, 3, 15),
                forwarding_window_start=datetime.date(2024, 3, 5),
                forwarding_window_end=datetime.date(2024, 3, 10),
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

        client = APIClient()
        client.force_authenticate(user=ops_user)
        response = client.get(OPERATIONS_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 30
        assert len(response.data['results']) == 25
        assert response.data['next'] is not None

    def test_returns_all_related_fields(self, ops_user, master_data):
        """Verify serializer returns related model data when populated."""
        from master_data.models import (
            Consignee,
            ContainerType,
            Forwarder,
            Port,
            Vessel,
        )
        from bookings.models import Container

        fpd = Port.objects.create(name='Hamburg Port', code='DEHAM', country='Germany')
        vessel = Vessel.objects.create(name='MSC Diana', imo_number='1234567')
        consignee = Consignee.objects.create(name='Test Consignee')
        forwarder = Forwarder.objects.create(name='DHL Forwarding', country='Germany')
        container_type = ContainerType.objects.create(name='Dry', code='DRY')

        booking = Booking.objects.create(
            booking_date=datetime.date(2024, 3, 1),
            booking_validity_date=datetime.date(2024, 3, 15),
            forwarding_window_start=datetime.date(2024, 3, 5),
            forwarding_window_end=datetime.date(2024, 3, 10),
            shipping_line=master_data['shipping_line'],
            pol=master_data['pol'],
            pod=master_data['pod'],
            client=master_data['client'],
            commodity=master_data['commodity'],
            cargo_type='FCL',
            shipment_type='Direct',
            stuffing_type='Factory',
            vessel=vessel,
            fpd=fpd,
            consignee=consignee,
            nvocc_forwarder=forwarder,
            voyage='V123W',
            etd_pol=datetime.datetime(2024, 3, 10, 8, 0, tzinfo=datetime.timezone.utc),
            eta_destination=datetime.datetime(2024, 3, 25, 14, 0, tzinfo=datetime.timezone.utc),
            created_by=ops_user,
        )

        Container.objects.create(
            booking=booking,
            container_type=container_type,
            container_size='20FT',
            container_count=1,
        )

        client = APIClient()
        client.force_authenticate(user=ops_user)
        response = client.get(OPERATIONS_URL)
        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        assert len(results) == 1
        data = results[0]
        assert data['booking_number'] == booking.job_number
        assert data['shipping_line'] == 'Maersk'
        assert data['pol'] == 'Mumbai Port'
        assert data['pod'] == 'Rotterdam Port'
        assert data['fpd'] == 'Hamburg Port'
        assert data['vessel_name'] == 'MSC Diana'
        assert data['consignee'] == 'Test Consignee'
        assert data['forwarder'] == 'DHL Forwarding'
        assert data['container_type'] == 'Dry'
        assert data['voyage'] == 'V123W'
        assert data['etd'] is not None
        assert data['eta'] is not None


class TestOperationsViewFiltering:
    """Test filtering support on the operations tracking view."""

    @pytest.fixture
    def filter_data(self, master_data, ops_user):
        """Create multiple bookings with different attributes for filter tests."""
        client2 = Client.objects.create(name='Second Client', email='client2@test.com')
        shipping_line2 = ShippingLine.objects.create(name='MSC', code='MSCU')
        pol2 = Port.objects.create(name='Chennai Port', code='INMAA', country='India')

        booking1 = Booking.objects.create(
            booking_date=datetime.date(2024, 3, 1),
            booking_validity_date=datetime.date(2024, 3, 15),
            forwarding_window_start=datetime.date(2024, 3, 5),
            forwarding_window_end=datetime.date(2024, 3, 10),
            shipping_line=master_data['shipping_line'],
            pol=master_data['pol'],
            pod=master_data['pod'],
            client=master_data['client'],
            commodity=master_data['commodity'],
            cargo_type='FCL',
            shipment_type='Direct',
            stuffing_type='Factory',
            status=Booking.Status.BOOKED,
            etd_pol=datetime.datetime(2024, 3, 10, 8, 0, tzinfo=datetime.timezone.utc),
            created_by=ops_user,
        )
        booking2 = Booking.objects.create(
            booking_date=datetime.date(2024, 4, 1),
            booking_validity_date=datetime.date(2024, 4, 15),
            forwarding_window_start=datetime.date(2024, 4, 5),
            forwarding_window_end=datetime.date(2024, 4, 10),
            shipping_line=shipping_line2,
            pol=pol2,
            pod=master_data['pod'],
            client=client2,
            commodity=master_data['commodity'],
            cargo_type='FCL',
            shipment_type='Direct',
            stuffing_type='Factory',
            status=Booking.Status.SHIPPED,
            etd_pol=datetime.datetime(2024, 4, 10, 8, 0, tzinfo=datetime.timezone.utc),
            created_by=ops_user,
        )
        return {
            'booking1': booking1,
            'booking2': booking2,
            'client2': client2,
            'shipping_line2': shipping_line2,
            'pol2': pol2,
        }

    def test_filter_by_customer(self, ops_user, master_data, filter_data):
        client = APIClient()
        client.force_authenticate(user=ops_user)
        response = client.get(OPERATIONS_URL, {'customer': master_data['client'].id})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['booking_number'] == filter_data['booking1'].job_number

    def test_filter_by_shipping_line(self, ops_user, filter_data):
        client = APIClient()
        client.force_authenticate(user=ops_user)
        response = client.get(OPERATIONS_URL, {'shipping_line': filter_data['shipping_line2'].id})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['booking_number'] == filter_data['booking2'].job_number

    def test_filter_by_status(self, ops_user, filter_data):
        client = APIClient()
        client.force_authenticate(user=ops_user)
        response = client.get(OPERATIONS_URL, {'status': 'SHIPPED'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['booking_number'] == filter_data['booking2'].job_number

    def test_filter_by_etd_from(self, ops_user, filter_data):
        client = APIClient()
        client.force_authenticate(user=ops_user)
        response = client.get(OPERATIONS_URL, {'etd_from': '2024-04-01T00:00:00Z'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['booking_number'] == filter_data['booking2'].job_number

    def test_filter_by_etd_to(self, ops_user, filter_data):
        client = APIClient()
        client.force_authenticate(user=ops_user)
        response = client.get(OPERATIONS_URL, {'etd_to': '2024-03-15T00:00:00Z'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['booking_number'] == filter_data['booking1'].job_number

    def test_filter_by_etd_range(self, ops_user, filter_data):
        client = APIClient()
        client.force_authenticate(user=ops_user)
        response = client.get(OPERATIONS_URL, {
            'etd_from': '2024-03-01T00:00:00Z',
            'etd_to': '2024-04-15T00:00:00Z',
        })
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2

    def test_filter_by_pol(self, ops_user, master_data, filter_data):
        client = APIClient()
        client.force_authenticate(user=ops_user)
        response = client.get(OPERATIONS_URL, {'pol': master_data['pol'].id})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['booking_number'] == filter_data['booking1'].job_number

    def test_filter_combined(self, ops_user, master_data, filter_data):
        """Test combining multiple filters."""
        client = APIClient()
        client.force_authenticate(user=ops_user)
        response = client.get(OPERATIONS_URL, {
            'customer': master_data['client'].id,
            'status': 'BOOKED',
        })
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['booking_number'] == filter_data['booking1'].job_number

    def test_filter_no_results(self, ops_user, filter_data):
        """Filters that match nothing return empty results."""
        client = APIClient()
        client.force_authenticate(user=ops_user)
        response = client.get(OPERATIONS_URL, {'status': 'COMPLETED'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0

    def test_no_filter_returns_all(self, ops_user, filter_data):
        """No filter parameters returns all bookings."""
        client = APIClient()
        client.force_authenticate(user=ops_user)
        response = client.get(OPERATIONS_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2


class TestOperationsViewOrdering:
    """Test ordering/sorting support on the operations tracking view."""

    @pytest.fixture
    def ordering_data(self, master_data, ops_user):
        """Create bookings with different values to test ordering."""
        from master_data.models import Port, Vessel

        pol2 = Port.objects.create(name='Chennai Port', code='INMAA', country='India')
        vessel_a = Vessel.objects.create(name='Alpha Vessel', imo_number='1111111')
        vessel_z = Vessel.objects.create(name='Zulu Vessel', imo_number='9999999')

        booking1 = Booking.objects.create(
            booking_date=datetime.date(2024, 3, 1),
            booking_validity_date=datetime.date(2024, 3, 15),
            forwarding_window_start=datetime.date(2024, 3, 5),
            forwarding_window_end=datetime.date(2024, 3, 10),
            shipping_line=master_data['shipping_line'],
            pol=master_data['pol'],
            pod=master_data['pod'],
            client=master_data['client'],
            commodity=master_data['commodity'],
            cargo_type='FCL',
            shipment_type='Direct',
            stuffing_type='Factory',
            vessel=vessel_a,
            voyage='V001',
            etd_pol=datetime.datetime(2024, 3, 10, 8, 0, tzinfo=datetime.timezone.utc),
            eta_destination=datetime.datetime(2024, 3, 25, 14, 0, tzinfo=datetime.timezone.utc),
            created_by=ops_user,
        )
        booking2 = Booking.objects.create(
            booking_date=datetime.date(2024, 4, 1),
            booking_validity_date=datetime.date(2024, 4, 15),
            forwarding_window_start=datetime.date(2024, 4, 5),
            forwarding_window_end=datetime.date(2024, 4, 10),
            shipping_line=master_data['shipping_line'],
            pol=pol2,
            pod=master_data['pod'],
            client=master_data['client'],
            commodity=master_data['commodity'],
            cargo_type='FCL',
            shipment_type='Direct',
            stuffing_type='Factory',
            vessel=vessel_z,
            voyage='V002',
            etd_pol=datetime.datetime(2024, 4, 10, 8, 0, tzinfo=datetime.timezone.utc),
            eta_destination=datetime.datetime(2024, 4, 25, 14, 0, tzinfo=datetime.timezone.utc),
            created_by=ops_user,
        )
        return {
            'booking1': booking1,
            'booking2': booking2,
        }

    def test_ordering_by_vessel_name_ascending(self, ops_user, ordering_data):
        """Test sorting by vessel_name in ascending order."""
        client = APIClient()
        client.force_authenticate(user=ops_user)
        response = client.get(OPERATIONS_URL, {'ordering': 'vessel_name'})
        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        assert len(results) == 2
        assert results[0]['vessel_name'] == 'Alpha Vessel'
        assert results[1]['vessel_name'] == 'Zulu Vessel'

    def test_ordering_by_vessel_name_descending(self, ops_user, ordering_data):
        """Test sorting by vessel_name in descending order."""
        client = APIClient()
        client.force_authenticate(user=ops_user)
        response = client.get(OPERATIONS_URL, {'ordering': '-vessel_name'})
        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        assert len(results) == 2
        assert results[0]['vessel_name'] == 'Zulu Vessel'
        assert results[1]['vessel_name'] == 'Alpha Vessel'

    def test_ordering_by_etd_ascending(self, ops_user, ordering_data):
        """Test sorting by etd in ascending order."""
        client = APIClient()
        client.force_authenticate(user=ops_user)
        response = client.get(OPERATIONS_URL, {'ordering': 'etd'})
        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        assert len(results) == 2
        # booking1 has earlier ETD
        assert results[0]['booking_number'] == ordering_data['booking1'].job_number
        assert results[1]['booking_number'] == ordering_data['booking2'].job_number

    def test_ordering_by_etd_descending(self, ops_user, ordering_data):
        """Test sorting by etd in descending order."""
        client = APIClient()
        client.force_authenticate(user=ops_user)
        response = client.get(OPERATIONS_URL, {'ordering': '-etd'})
        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        assert len(results) == 2
        # booking2 has later ETD
        assert results[0]['booking_number'] == ordering_data['booking2'].job_number
        assert results[1]['booking_number'] == ordering_data['booking1'].job_number

    def test_ordering_by_pol_ascending(self, ops_user, ordering_data):
        """Test sorting by POL name in ascending order."""
        client = APIClient()
        client.force_authenticate(user=ops_user)
        response = client.get(OPERATIONS_URL, {'ordering': 'pol'})
        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        assert len(results) == 2
        # Chennai Port < Mumbai Port alphabetically
        assert results[0]['pol'] == 'Chennai Port'
        assert results[1]['pol'] == 'Mumbai Port'

    def test_ordering_by_voyage_ascending(self, ops_user, ordering_data):
        """Test sorting by voyage in ascending order."""
        client = APIClient()
        client.force_authenticate(user=ops_user)
        response = client.get(OPERATIONS_URL, {'ordering': 'voyage'})
        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        assert len(results) == 2
        assert results[0]['voyage'] == 'V001'
        assert results[1]['voyage'] == 'V002'

    def test_default_ordering_by_booking_date_desc(self, ops_user, ordering_data):
        """Test default ordering is by booking_date descending."""
        client = APIClient()
        client.force_authenticate(user=ops_user)
        response = client.get(OPERATIONS_URL)
        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        assert len(results) == 2
        # booking2 has later booking_date (2024-04-01) so appears first
        assert results[0]['booking_number'] == ordering_data['booking2'].job_number
        assert results[1]['booking_number'] == ordering_data['booking1'].job_number
