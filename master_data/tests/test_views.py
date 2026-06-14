import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APIClient

from master_data.models import Client, Port, ShippingLine

User = get_user_model()


@pytest.fixture
def admin_group(db):
    return Group.objects.create(name='Admin')


@pytest.fixture
def operations_group(db):
    return Group.objects.create(name='Operations')


@pytest.fixture
def admin_user(db, admin_group):
    user = User.objects.create_user(username='admin', password='testpass123')
    user.groups.add(admin_group)
    return user


@pytest.fixture
def operations_user(db, operations_group):
    user = User.objects.create_user(username='ops_user', password='testpass123')
    user.groups.add(operations_group)
    return user


@pytest.fixture
def admin_client(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def ops_client(operations_user):
    client = APIClient()
    client.force_authenticate(user=operations_user)
    return client


@pytest.fixture
def unauthenticated_client():
    return APIClient()


@pytest.fixture
def sample_client(db):
    return Client.objects.create(name='Test Client', email='test@example.com')


@pytest.fixture
def sample_port(db):
    return Port.objects.create(name='Mumbai Port', code='INMUN', country='India')


@pytest.fixture
def sample_shipping_line(db):
    return ShippingLine.objects.create(name='Maersk', code='MAEU')


class TestMasterDataListAndRetrieve:
    """Test read access for authenticated users."""

    def test_list_entities_authenticated(self, ops_client, sample_client):
        """Any authenticated user can list entities."""
        response = ops_client.get('/api/master-data/clients/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['name'] == 'Test Client'

    def test_list_entities_unauthenticated(self, unauthenticated_client, sample_client):
        """Unauthenticated users cannot access the API."""
        response = unauthenticated_client.get('/api/master-data/clients/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_entity(self, ops_client, sample_client):
        """Any authenticated user can retrieve a single entity."""
        response = ops_client.get(f'/api/master-data/clients/{sample_client.pk}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Test Client'
        assert response.data['email'] == 'test@example.com'

    def test_invalid_entity_type_returns_404(self, ops_client):
        """Invalid entity type slug returns 404."""
        response = ops_client.get('/api/master-data/invalid-type/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestMasterDataCreate:
    """Test create access (Admin only)."""

    def test_admin_can_create(self, admin_client):
        """Admin users can create entities."""
        response = admin_client.post(
            '/api/master-data/clients/',
            {'name': 'New Client', 'email': 'new@example.com'},
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Client'
        assert Client.objects.filter(name='New Client').exists()

    def test_non_admin_cannot_create(self, ops_client):
        """Non-admin users cannot create entities."""
        response = ops_client.post(
            '/api/master-data/clients/',
            {'name': 'New Client'},
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestMasterDataUpdate:
    """Test update access (Admin only)."""

    def test_admin_can_update(self, admin_client, sample_client):
        """Admin users can update entities."""
        response = admin_client.patch(
            f'/api/master-data/clients/{sample_client.pk}/',
            {'name': 'Updated Client'},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        sample_client.refresh_from_db()
        assert sample_client.name == 'Updated Client'

    def test_non_admin_cannot_update(self, ops_client, sample_client):
        """Non-admin users cannot update entities."""
        response = ops_client.patch(
            f'/api/master-data/clients/{sample_client.pk}/',
            {'name': 'Hacked Name'},
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestMasterDataDelete:
    """Test delete access and deletion protection."""

    def test_admin_can_delete_unreferenced(self, admin_client, sample_client):
        """Admin can delete an entity not referenced by bookings."""
        response = admin_client.delete(
            f'/api/master-data/clients/{sample_client.pk}/'
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Client.objects.filter(pk=sample_client.pk).exists()

    def test_non_admin_cannot_delete(self, ops_client, sample_client):
        """Non-admin users cannot delete entities."""
        response = ops_client.delete(
            f'/api/master-data/clients/{sample_client.pk}/'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_referenced_entity_returns_409(
        self, admin_client, admin_user, sample_client, sample_port, sample_shipping_line
    ):
        """Deleting an entity referenced by a booking returns 409 Conflict."""
        from bookings.models import Booking

        # Create a second port for POD
        pod = Port.objects.create(name='Rotterdam', code='NLRTM', country='Netherlands')
        from master_data.models import Commodity

        commodity = Commodity.objects.create(name='Electronics')

        Booking.objects.create(
            booking_date='2024-01-01',
            booking_validity_date='2024-02-01',
            forwarding_window_start='2024-01-15',
            forwarding_window_end='2024-01-30',
            shipping_line=sample_shipping_line,
            pol=sample_port,
            pod=pod,
            client=sample_client,
            commodity=commodity,
            cargo_type='FCL',
            shipment_type='Direct',
            stuffing_type='Factory',
            created_by=admin_user,
        )

        # Attempt to delete client — should get 409
        response = admin_client.delete(
            f'/api/master-data/clients/{sample_client.pk}/'
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        assert 'Cannot delete' in response.data['detail']
        # Entity still exists
        assert Client.objects.filter(pk=sample_client.pk).exists()


class TestMasterDataFiltering:
    """Test filtering by name."""

    def test_filter_by_name(self, ops_client, db):
        """Filtering by name (case-insensitive contains)."""
        Client.objects.create(name='Alpha Corp')
        Client.objects.create(name='Beta Industries')
        Client.objects.create(name='Alphabetical LLC')

        response = ops_client.get('/api/master-data/clients/?name=alpha')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2
        names = [r['name'] for r in response.data['results']]
        assert 'Alpha Corp' in names
        assert 'Alphabetical LLC' in names

    def test_filter_no_match(self, ops_client, sample_client):
        """Filter that matches nothing returns empty results."""
        response = ops_client.get('/api/master-data/clients/?name=nonexistent')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0


class TestMasterDataOrdering:
    """Test ordering by name and created_at."""

    def test_order_by_name_ascending(self, ops_client, db):
        """Default ordering is by name ascending."""
        Client.objects.create(name='Zeta')
        Client.objects.create(name='Alpha')
        Client.objects.create(name='Mu')

        response = ops_client.get('/api/master-data/clients/?ordering=name')
        assert response.status_code == status.HTTP_200_OK
        names = [r['name'] for r in response.data['results']]
        assert names == ['Alpha', 'Mu', 'Zeta']

    def test_order_by_name_descending(self, ops_client, db):
        """Ordering by -name gives descending."""
        Client.objects.create(name='Zeta')
        Client.objects.create(name='Alpha')

        response = ops_client.get('/api/master-data/clients/?ordering=-name')
        assert response.status_code == status.HTTP_200_OK
        names = [r['name'] for r in response.data['results']]
        assert names == ['Zeta', 'Alpha']

    def test_order_by_created_at(self, ops_client, db):
        """Ordering by created_at."""
        Client.objects.create(name='First')
        Client.objects.create(name='Second')

        response = ops_client.get('/api/master-data/clients/?ordering=created_at')
        assert response.status_code == status.HTTP_200_OK
        names = [r['name'] for r in response.data['results']]
        assert names == ['First', 'Second']


class TestMasterDataPagination:
    """Test that pagination is applied."""

    def test_response_is_paginated(self, ops_client, sample_client):
        """Response includes pagination fields."""
        response = ops_client.get('/api/master-data/clients/')
        assert response.status_code == status.HTTP_200_OK
        assert 'count' in response.data
        assert 'next' in response.data
        assert 'previous' in response.data
        assert 'results' in response.data


class TestMultipleEntityTypes:
    """Test that different entity type slugs route correctly."""

    def test_ports_endpoint(self, ops_client, sample_port):
        response = ops_client.get('/api/master-data/ports/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['results'][0]['name'] == 'Mumbai Port'
        assert response.data['results'][0]['code'] == 'INMUN'

    def test_shipping_lines_endpoint(self, ops_client, sample_shipping_line):
        response = ops_client.get('/api/master-data/shipping-lines/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['results'][0]['name'] == 'Maersk'

    def test_create_port_as_admin(self, admin_client):
        response = admin_client.post(
            '/api/master-data/ports/',
            {'name': 'Shanghai', 'code': 'CNSHA', 'country': 'China'},
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert Port.objects.filter(name='Shanghai').exists()
