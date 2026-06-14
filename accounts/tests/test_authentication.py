"""
Tests for JWT authentication, user management, and role-based access.
Validates Requirements 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APIClient

from master_data.models import (
    Client,
    Commodity,
    MarketingPerson,
    Port,
    ShippingLine,
)
from bookings.models import Booking

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(
        username='admin_auth', password='securepass123', email='admin@test.com'
    )
    group, _ = Group.objects.get_or_create(name='Admin')
    user.groups.add(group)
    return user


@pytest.fixture
def ops_user(db):
    user = User.objects.create_user(
        username='ops_auth', password='securepass123', email='ops@test.com'
    )
    group, _ = Group.objects.get_or_create(name='Operations')
    user.groups.add(group)
    return user


@pytest.fixture
def sales_user(db):
    user = User.objects.create_user(
        username='sales_auth', password='securepass123', email='sales@test.com'
    )
    group, _ = Group.objects.get_or_create(name='Sales')
    user.groups.add(group)
    return user


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client


class TestJWTTokenEndpoints:
    """Tests for JWT token obtain and refresh endpoints (Req 12.1)."""

    def test_obtain_token_valid_credentials(self, api_client, admin_user):
        """Valid credentials return access and refresh tokens."""
        response = api_client.post(
            '/api/accounts/token/',
            {'username': 'admin_auth', 'password': 'securepass123'},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_obtain_token_invalid_credentials(self, api_client, admin_user):
        """Invalid credentials return 401."""
        response = api_client.post(
            '/api/accounts/token/',
            {'username': 'admin_auth', 'password': 'wrongpass'},
            format='json',
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token(self, api_client, admin_user):
        """Refresh token returns a new access token."""
        # Get initial tokens
        token_response = api_client.post(
            '/api/accounts/token/',
            {'username': 'admin_auth', 'password': 'securepass123'},
            format='json',
        )
        refresh_token = token_response.data['refresh']

        # Refresh
        response = api_client.post(
            '/api/accounts/token/refresh/',
            {'refresh': refresh_token},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data

    def test_access_with_jwt_token(self, api_client, ops_user):
        """Authenticated request with JWT token succeeds."""
        # Obtain token
        token_response = api_client.post(
            '/api/accounts/token/',
            {'username': 'ops_auth', 'password': 'securepass123'},
            format='json',
        )
        access_token = token_response.data['access']

        # Use token to access protected endpoint
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = api_client.get('/api/master-data/clients/')
        assert response.status_code == status.HTTP_200_OK


class TestUnauthenticatedAccess:
    """Tests that unauthenticated requests are rejected with 401 (Req 12.5)."""

    def test_unauthenticated_request_returns_401(self, api_client):
        """Unauthenticated request to a protected endpoint returns 401."""
        response = api_client.get('/api/bookings/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_token_returns_401(self, api_client):
        """Request with invalid JWT token returns 401."""
        api_client.credentials(HTTP_AUTHORIZATION='Bearer invalid-token-here')
        response = api_client.get('/api/bookings/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestUnauthorizedAccess:
    """Tests that authenticated but unauthorized requests are rejected with 403 (Req 12.5)."""

    def test_sales_user_cannot_create_booking(self, api_client, sales_user):
        """Sales user gets 403 when trying to create a booking."""
        api_client.force_authenticate(user=sales_user)
        response = api_client.post('/api/bookings/', {}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_ops_user_cannot_manage_master_data(self, api_client, ops_user):
        """Ops user gets 403 when trying to create master data."""
        api_client.force_authenticate(user=ops_user)
        response = api_client.post(
            '/api/master-data/clients/',
            {'name': 'New Client'},
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestUserManagement:
    """Tests for admin user management endpoints (Req 12.6, 12.7)."""

    def test_admin_can_list_users(self, admin_client):
        """Admin can list all users."""
        response = admin_client.get('/api/accounts/users/')
        assert response.status_code == status.HTTP_200_OK

    def test_admin_can_create_user(self, admin_client):
        """Admin can create a new user with role."""
        response = admin_client.post(
            '/api/accounts/users/',
            {
                'username': 'new_user',
                'password': 'newpass123',
                'email': 'new@test.com',
                'first_name': 'New',
                'last_name': 'User',
                'role': 'Operations',
            },
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['username'] == 'new_user'
        assert response.data['role'] == 'Operations'

        # Verify user can authenticate
        new_user = User.objects.get(username='new_user')
        assert new_user.check_password('newpass123')
        assert new_user.groups.filter(name='Operations').exists()

    def test_admin_can_assign_role(self, admin_client, ops_user):
        """Admin can change a user's role."""
        response = admin_client.patch(
            f'/api/accounts/users/{ops_user.pk}/role/',
            {'role': 'Sales'},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['role'] == 'Sales'

        # Verify old role is removed
        ops_user.refresh_from_db()
        assert not ops_user.groups.filter(name='Operations').exists()
        assert ops_user.groups.filter(name='Sales').exists()

    def test_non_admin_cannot_list_users(self, api_client, ops_user):
        """Non-admin user cannot access user management."""
        api_client.force_authenticate(user=ops_user)
        response = api_client.get('/api/accounts/users/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_non_admin_cannot_create_users(self, api_client, ops_user):
        """Non-admin user cannot create users."""
        api_client.force_authenticate(user=ops_user)
        response = api_client.post(
            '/api/accounts/users/',
            {
                'username': 'hacker',
                'password': 'hax0r123',
                'role': 'Admin',
            },
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_user_invalid_role(self, admin_client):
        """Creating a user with an invalid role is rejected."""
        response = admin_client.post(
            '/api/accounts/users/',
            {
                'username': 'bad_role_user',
                'password': 'testpass123',
                'role': 'SuperAdmin',
            },
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestSalesUserFiltering:
    """Tests for Sales user booking queryset filtering (Req 12.4)."""

    @pytest.fixture
    def master_data(self, db):
        shipping_line = ShippingLine.objects.create(name='Auth Maersk', code='MAER')
        pol = Port.objects.create(name='Auth Mumbai', code='INMUM', country='India')
        pod = Port.objects.create(name='Auth Rotterdam', code='NLRTM', country='NL')
        client = Client.objects.create(name='Auth Client')
        commodity = Commodity.objects.create(name='Auth Commodity', hs_code='8543')
        return {
            'shipping_line': shipping_line,
            'pol': pol,
            'pod': pod,
            'client': client,
            'commodity': commodity,
        }

    def test_sales_user_sees_only_their_bookings(
        self, api_client, sales_user, ops_user, master_data
    ):
        """Sales user only sees bookings where they are the marketing person."""
        # Create marketing person linked to sales user
        mp = MarketingPerson.objects.create(name='Sales MP Auth', user=sales_user)

        # Booking linked to sales user
        booking_mine = Booking(
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
            marketing_person=mp,
            created_by=ops_user,
        )
        booking_mine.save()

        # Booking NOT linked to sales user
        booking_other = Booking(
            booking_date='2024-03-02',
            booking_validity_date='2024-03-16',
            forwarding_window_start='2024-03-06',
            forwarding_window_end='2024-03-11',
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
        booking_other.save()

        api_client.force_authenticate(user=sales_user)
        response = api_client.get('/api/bookings/')

        assert response.status_code == status.HTTP_200_OK
        job_numbers = [b['job_number'] for b in response.data['results']]
        assert booking_mine.job_number in job_numbers
        assert booking_other.job_number not in job_numbers

    def test_ops_user_sees_all_bookings(
        self, api_client, ops_user, master_data
    ):
        """Operations user sees all bookings regardless of marketing person."""
        # Create two bookings
        for i in range(2):
            b = Booking(
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
            b.save()

        api_client.force_authenticate(user=ops_user)
        response = api_client.get('/api/bookings/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2
