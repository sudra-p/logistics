"""
Tests for transhipment management endpoints and validation.
"""

import pytest
from datetime import datetime, timedelta, timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from bookings.models import Booking, TranshipmentLeg
from master_data.models import (
    Client,
    Commodity,
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
    ts_port_1 = Port.objects.create(name='Singapore', code='SGSIN', country='Singapore')
    ts_port_2 = Port.objects.create(name='Colombo', code='LKCMB', country='Sri Lanka')
    ts_port_3 = Port.objects.create(name='Jeddah', code='SAJED', country='Saudi Arabia')
    ts_port_4 = Port.objects.create(name='Port Said', code='EGPSD', country='Egypt')
    return {
        'shipping_line': shipping_line,
        'pol': pol,
        'pod': pod,
        'client': client,
        'commodity': commodity,
        'ts_port_1': ts_port_1,
        'ts_port_2': ts_port_2,
        'ts_port_3': ts_port_3,
        'ts_port_4': ts_port_4,
    }


@pytest.fixture
def booking(db, ops_user, master_data):
    """Create a booking for testing."""
    from datetime import date

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


def _make_leg_data(port_id, eta_offset_hours=0, etd_offset_hours=1):
    """Helper to create leg data with given port and time offsets from a base time."""
    base = datetime(2024, 1, 10, 0, 0, 0, tzinfo=timezone.utc)
    return {
        'port': port_id,
        'eta': (base + timedelta(hours=eta_offset_hours)).isoformat(),
        'connecting_vessel_voyage': 'VESSEL-V001',
        'etd': (base + timedelta(hours=etd_offset_hours)).isoformat(),
    }


@pytest.mark.django_db
class TestAddTranshipments:
    """Tests for POST /api/bookings/{id}/transhipments/"""

    def test_successful_add_single_leg(self, api_client, booking, master_data):
        """Test successfully adding a single transhipment leg."""
        url = f'/api/bookings/{booking.id}/transhipments/'
        data = {
            'legs': [_make_leg_data(master_data['ts_port_1'].id, 0, 2)]
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == 201
        assert len(response.data) == 1
        assert response.data[0]['sequence'] == 1
        assert response.data[0]['port'] == master_data['ts_port_1'].id

    def test_successful_add_multiple_legs(self, api_client, booking, master_data):
        """Test successfully adding multiple transhipment legs in chronological order."""
        url = f'/api/bookings/{booking.id}/transhipments/'
        data = {
            'legs': [
                _make_leg_data(master_data['ts_port_1'].id, 0, 2),
                _make_leg_data(master_data['ts_port_2'].id, 3, 5),
                _make_leg_data(master_data['ts_port_3'].id, 6, 8),
            ]
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == 201
        assert len(response.data) == 3
        assert response.data[0]['sequence'] == 1
        assert response.data[1]['sequence'] == 2
        assert response.data[2]['sequence'] == 3

    def test_max_four_legs(self, api_client, booking, master_data):
        """Test that more than 4 legs are rejected."""
        url = f'/api/bookings/{booking.id}/transhipments/'
        data = {
            'legs': [
                _make_leg_data(master_data['ts_port_1'].id, 0, 2),
                _make_leg_data(master_data['ts_port_2'].id, 3, 5),
                _make_leg_data(master_data['ts_port_3'].id, 6, 8),
                _make_leg_data(master_data['ts_port_4'].id, 9, 11),
                _make_leg_data(master_data['ts_port_1'].id, 12, 14),
            ]
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == 400
        assert 'transhipment_legs' in response.data

    def test_max_four_legs_with_existing(self, api_client, booking, master_data):
        """Test that existing + new legs cannot exceed 4."""
        # Add 3 legs first
        url = f'/api/bookings/{booking.id}/transhipments/'
        data = {
            'legs': [
                _make_leg_data(master_data['ts_port_1'].id, 0, 2),
                _make_leg_data(master_data['ts_port_2'].id, 3, 5),
                _make_leg_data(master_data['ts_port_3'].id, 6, 8),
            ]
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == 201

        # Try to add 2 more (total would be 5)
        data = {
            'legs': [
                _make_leg_data(master_data['ts_port_4'].id, 9, 11),
                _make_leg_data(master_data['ts_port_1'].id, 12, 14),
            ]
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == 400

    def test_etd_before_eta_rejected(self, api_client, booking, master_data):
        """Test that a leg with ETD <= ETA is rejected."""
        url = f'/api/bookings/{booking.id}/transhipments/'
        # ETD (offset 0) <= ETA (offset 2) — invalid
        data = {
            'legs': [_make_leg_data(master_data['ts_port_1'].id, 2, 0)]
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == 400

    def test_etd_equal_eta_rejected(self, api_client, booking, master_data):
        """Test that ETD == ETA is rejected (must be strictly later)."""
        url = f'/api/bookings/{booking.id}/transhipments/'
        data = {
            'legs': [_make_leg_data(master_data['ts_port_1'].id, 2, 2)]
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == 400

    def test_chronological_ordering_violated(self, api_client, booking, master_data):
        """Test that legs not in chronological order are rejected."""
        url = f'/api/bookings/{booking.id}/transhipments/'
        # Second leg ETA (1) < first leg ETD (5)
        data = {
            'legs': [
                _make_leg_data(master_data['ts_port_1'].id, 0, 5),
                _make_leg_data(master_data['ts_port_2'].id, 1, 3),
            ]
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == 400

    def test_invalid_port_reference(self, api_client, booking, master_data):
        """Test that an invalid port ID is rejected."""
        url = f'/api/bookings/{booking.id}/transhipments/'
        data = {
            'legs': [{
                'port': 99999,
                'eta': '2024-01-10T00:00:00Z',
                'connecting_vessel_voyage': 'VESSEL-V001',
                'etd': '2024-01-10T02:00:00Z',
            }]
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == 400

    def test_missing_required_fields(self, api_client, booking, master_data):
        """Test that missing required fields are rejected."""
        url = f'/api/bookings/{booking.id}/transhipments/'
        # Missing connecting_vessel_voyage and etd
        data = {
            'legs': [{
                'port': master_data['ts_port_1'].id,
                'eta': '2024-01-10T00:00:00Z',
            }]
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == 400

    def test_booking_not_found(self, api_client, master_data):
        """Test 404 when booking doesn't exist."""
        url = '/api/bookings/99999/transhipments/'
        data = {
            'legs': [_make_leg_data(master_data['ts_port_1'].id, 0, 2)]
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == 404

    def test_direct_routing_when_no_legs(self, api_client, booking, master_data):
        """Test that a booking with no legs is considered DIRECT routing."""
        assert booking.transhipment_legs.count() == 0
        # A booking with 0 transhipment_legs is implicitly DIRECT


@pytest.mark.django_db
class TestUpdateTranshipment:
    """Tests for PUT /api/bookings/{id}/transhipments/{tid}/"""

    def test_successful_update(self, api_client, booking, master_data):
        """Test successfully updating a transhipment leg."""
        # First add a leg
        add_url = f'/api/bookings/{booking.id}/transhipments/'
        data = {
            'legs': [_make_leg_data(master_data['ts_port_1'].id, 0, 2)]
        }
        response = api_client.post(add_url, data, format='json')
        assert response.status_code == 201
        leg_id = response.data[0]['id']

        # Update the leg
        update_url = f'/api/bookings/{booking.id}/transhipments/{leg_id}/'
        update_data = {
            'port': master_data['ts_port_2'].id,
            'eta': '2024-01-10T01:00:00Z',
            'connecting_vessel_voyage': 'VESSEL-V002',
            'etd': '2024-01-10T04:00:00Z',
        }
        response = api_client.put(update_url, update_data, format='json')

        assert response.status_code == 200
        assert response.data['port'] == master_data['ts_port_2'].id
        assert response.data['connecting_vessel_voyage'] == 'VESSEL-V002'

    def test_update_violates_etd_eta(self, api_client, booking, master_data):
        """Test update rejected when ETD <= ETA."""
        # Add a leg
        add_url = f'/api/bookings/{booking.id}/transhipments/'
        data = {
            'legs': [_make_leg_data(master_data['ts_port_1'].id, 0, 2)]
        }
        response = api_client.post(add_url, data, format='json')
        leg_id = response.data[0]['id']

        # Update with ETD <= ETA
        update_url = f'/api/bookings/{booking.id}/transhipments/{leg_id}/'
        update_data = {
            'port': master_data['ts_port_1'].id,
            'eta': '2024-01-10T05:00:00Z',
            'connecting_vessel_voyage': 'VESSEL-V001',
            'etd': '2024-01-10T03:00:00Z',
        }
        response = api_client.put(update_url, update_data, format='json')

        assert response.status_code == 400

    def test_update_violates_chronological_order(self, api_client, booking, master_data):
        """Test update rejected when it breaks chronological order with adjacent legs."""
        # Add two legs
        add_url = f'/api/bookings/{booking.id}/transhipments/'
        data = {
            'legs': [
                _make_leg_data(master_data['ts_port_1'].id, 0, 2),
                _make_leg_data(master_data['ts_port_2'].id, 3, 5),
            ]
        }
        response = api_client.post(add_url, data, format='json')
        assert response.status_code == 201
        leg2_id = response.data[1]['id']

        # Update leg 2 so its ETA is before leg 1's ETD
        update_url = f'/api/bookings/{booking.id}/transhipments/{leg2_id}/'
        update_data = {
            'port': master_data['ts_port_2'].id,
            'eta': '2024-01-10T00:30:00Z',  # Before leg 1 ETD (02:00)
            'connecting_vessel_voyage': 'VESSEL-V001',
            'etd': '2024-01-10T01:30:00Z',
        }
        response = api_client.put(update_url, update_data, format='json')

        assert response.status_code == 400

    def test_update_leg_not_found(self, api_client, booking, master_data):
        """Test 404 when leg doesn't exist."""
        update_url = f'/api/bookings/{booking.id}/transhipments/99999/'
        update_data = {
            'port': master_data['ts_port_1'].id,
            'eta': '2024-01-10T00:00:00Z',
            'connecting_vessel_voyage': 'VESSEL-V001',
            'etd': '2024-01-10T02:00:00Z',
        }
        response = api_client.put(update_url, update_data, format='json')

        assert response.status_code == 404


@pytest.mark.django_db
class TestDeleteTranshipment:
    """Tests for DELETE /api/bookings/{id}/transhipments/{tid}/"""

    def test_successful_delete(self, api_client, booking, master_data):
        """Test successfully deleting a transhipment leg."""
        # Add a leg
        add_url = f'/api/bookings/{booking.id}/transhipments/'
        data = {
            'legs': [_make_leg_data(master_data['ts_port_1'].id, 0, 2)]
        }
        response = api_client.post(add_url, data, format='json')
        leg_id = response.data[0]['id']

        # Delete the leg
        delete_url = f'/api/bookings/{booking.id}/transhipments/{leg_id}/'
        response = api_client.delete(delete_url)

        assert response.status_code == 204
        assert booking.transhipment_legs.count() == 0

    def test_delete_resequences_remaining_legs(self, api_client, booking, master_data):
        """Test that deleting a leg re-sequences the remaining legs."""
        # Add 3 legs
        add_url = f'/api/bookings/{booking.id}/transhipments/'
        data = {
            'legs': [
                _make_leg_data(master_data['ts_port_1'].id, 0, 2),
                _make_leg_data(master_data['ts_port_2'].id, 3, 5),
                _make_leg_data(master_data['ts_port_3'].id, 6, 8),
            ]
        }
        response = api_client.post(add_url, data, format='json')
        assert response.status_code == 201
        leg1_id = response.data[0]['id']

        # Delete leg 1
        delete_url = f'/api/bookings/{booking.id}/transhipments/{leg1_id}/'
        response = api_client.delete(delete_url)
        assert response.status_code == 204

        # Verify resequencing
        remaining_legs = booking.transhipment_legs.order_by('sequence')
        sequences = list(remaining_legs.values_list('sequence', flat=True))
        assert sequences == [1, 2]

    def test_delete_leg_not_found(self, api_client, booking):
        """Test 404 when leg doesn't exist."""
        delete_url = f'/api/bookings/{booking.id}/transhipments/99999/'
        response = api_client.delete(delete_url)

        assert response.status_code == 404


@pytest.mark.django_db
class TestListTranshipments:
    """Tests for GET /api/bookings/{id}/transhipments/"""

    def test_list_empty(self, api_client, booking):
        """Test listing transhipment legs when none exist."""
        url = f'/api/bookings/{booking.id}/transhipments/'
        response = api_client.get(url)

        assert response.status_code == 200
        assert response.data == []

    def test_list_with_legs(self, api_client, booking, master_data):
        """Test listing transhipment legs after adding some."""
        add_url = f'/api/bookings/{booking.id}/transhipments/'
        data = {
            'legs': [
                _make_leg_data(master_data['ts_port_1'].id, 0, 2),
                _make_leg_data(master_data['ts_port_2'].id, 3, 5),
            ]
        }
        api_client.post(add_url, data, format='json')

        response = api_client.get(add_url)

        assert response.status_code == 200
        assert len(response.data) == 2
        assert response.data[0]['sequence'] == 1
        assert response.data[1]['sequence'] == 2
