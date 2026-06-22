"""
Tests for role-based access control on all new endpoints.
Task 25.12: Verify that endpoint-level RBAC restricts access properly.
"""

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APIClient

from bookings.models import Booking, Container
from inventory.models import StockItem
from master_data.models import Client, Commodity, ContainerType, Port, ShippingLine
from proforma.models import ProformaInvoice, ProformaLineItem

User = get_user_model()


@pytest.fixture
def ops_user(db):
    user = User.objects.create_user(username='ops_user', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Operations')
    user.groups.add(group)
    return user


@pytest.fixture
def accounts_user(db):
    user = User.objects.create_user(username='acc_user', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Accounts')
    user.groups.add(group)
    return user


@pytest.fixture
def sales_user(db):
    user = User.objects.create_user(username='sales_user', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Sales')
    user.groups.add(group)
    return user


@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(username='admin_user', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Admin')
    user.groups.add(group)
    return user


@pytest.fixture
def master_data(db):
    shipping_line = ShippingLine.objects.create(name='Maersk', code='MAEU')
    pol = Port.objects.create(name='Mumbai Port', code='INMUN', country='India')
    pod = Port.objects.create(name='Rotterdam Port', code='NLRTM', country='Netherlands')
    client_obj = Client.objects.create(name='Test Client', email='client@test.com')
    commodity = Commodity.objects.create(name='Electronics', hs_code='8542')
    container_type = ContainerType.objects.create(name='Dry', code='DRY')
    return {
        'shipping_line': shipping_line,
        'pol': pol,
        'pod': pod,
        'client': client_obj,
        'commodity': commodity,
        'container_type': container_type,
    }


def _make_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestProformaEndpointRBAC:
    """Tests for Proforma Invoice endpoint access control."""

    def test_accounts_user_can_create_pi(self, accounts_user, master_data):
        """Accounts user can create a Proforma Invoice."""
        client = _make_client(accounts_user)
        response = client.post('/api/proforma-invoices/', {
            'date': '2024-06-01',
            'customer': master_data['client'].pk,
            'currency': 'USD',
            'exchange_rate': '83.5000',
            'payment_terms': 'Net 30',
            'expected_shipment_date': '2024-07-01',
            'line_items': [
                {'product_name': 'Widget', 'quantity': '10.000', 'rate': '100.00', 'amount': '1000.00'}
            ],
        }, format='json')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_operations_user_cannot_create_pi(self, ops_user, master_data):
        """Operations user is denied write access to Proforma Invoices."""
        client = _make_client(ops_user)
        response = client.post('/api/proforma-invoices/', {
            'date': '2024-06-01',
            'customer': master_data['client'].pk,
            'currency': 'USD',
            'exchange_rate': '83.5000',
            'payment_terms': 'Net 30',
            'expected_shipment_date': '2024-07-01',
            'line_items': [
                {'product_name': 'Widget', 'quantity': '10.000', 'rate': '100.00', 'amount': '1000.00'}
            ],
        }, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_sales_user_cannot_create_pi(self, sales_user, master_data):
        """Sales user is denied write access to Proforma Invoices."""
        client = _make_client(sales_user)
        response = client.post('/api/proforma-invoices/', {
            'date': '2024-06-01',
            'customer': master_data['client'].pk,
            'currency': 'USD',
            'exchange_rate': '83.5000',
            'payment_terms': 'Net 30',
            'expected_shipment_date': '2024-07-01',
            'line_items': [
                {'product_name': 'Widget', 'quantity': '10.000', 'rate': '100.00', 'amount': '1000.00'}
            ],
        }, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_access_pi(self, master_data):
        """Unauthenticated user is denied access."""
        client = APIClient()
        response = client.get('/api/proforma-invoices/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestPaymentEndpointRBAC:
    """Tests for Payment endpoint access control."""

    def test_operations_user_cannot_create_payment(self, ops_user, accounts_user, master_data):
        """Operations user cannot create payments."""
        # Create a PI first
        pi = ProformaInvoice(
            date=datetime.date.today(),
            customer=master_data['client'],
            currency='USD',
            payment_terms='Net 30',
            expected_shipment_date=datetime.date.today(),
            status=ProformaInvoice.Status.APPROVED,
            created_by=accounts_user,
        )
        pi.save()
        ProformaLineItem.objects.create(
            proforma_invoice=pi, product_name='Widget',
            quantity=Decimal('10.000'), rate=Decimal('100.00'), amount=Decimal('1000.00'),
        )
        pi.total_amount = Decimal('1000.00')
        pi.save(update_fields=['total_amount'])

        client = _make_client(ops_user)
        response = client.post('/api/payments/', {
            'proforma_invoice': pi.pk,
            'amount': '500.00',
            'payment_mode': 'BANK',
            'payment_date': '2024-06-01',
        }, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_accounts_user_can_create_payment(self, accounts_user, master_data):
        """Accounts user can create payments."""
        pi = ProformaInvoice(
            date=datetime.date.today(),
            customer=master_data['client'],
            currency='USD',
            payment_terms='Net 30',
            expected_shipment_date=datetime.date.today(),
            status=ProformaInvoice.Status.APPROVED,
            created_by=accounts_user,
        )
        pi.save()
        ProformaLineItem.objects.create(
            proforma_invoice=pi, product_name='Widget',
            quantity=Decimal('10.000'), rate=Decimal('100.00'), amount=Decimal('1000.00'),
        )
        pi.total_amount = Decimal('1000.00')
        pi.save(update_fields=['total_amount'])

        client = _make_client(accounts_user)
        response = client.post('/api/payments/', {
            'proforma_invoice': pi.pk,
            'amount': '500.00',
            'payment_mode': 'BANK',
            'payment_date': '2024-06-01',
        }, format='json')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]


@pytest.mark.django_db
class TestStockEndpointRBAC:
    """Tests for Stock/Inventory endpoint access control."""

    def test_operations_user_can_access_stock(self, ops_user):
        """Operations user can access stock items."""
        client = _make_client(ops_user)
        response = client.get('/api/stock-items/')
        assert response.status_code == status.HTTP_200_OK

    def test_accounts_user_cannot_access_stock(self, accounts_user):
        """Accounts user is denied access to stock management."""
        client = _make_client(accounts_user)
        response = client.get('/api/stock-items/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_sales_user_cannot_access_stock(self, sales_user):
        """Sales user is denied access to stock management."""
        client = _make_client(sales_user)
        response = client.get('/api/stock-items/')
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestStuffingEndpointRBAC:
    """Tests for stuffing action endpoint access control."""

    def test_accounts_user_cannot_perform_stuffing(self, accounts_user, ops_user, master_data):
        """Accounts user cannot perform stuffing."""
        today = datetime.date.today()
        booking = Booking.objects.create(
            status=Booking.Status.STUFFING,
            booking_date=today,
            booking_validity_date=today,
            forwarding_window_start=today,
            forwarding_window_end=today,
            shipping_line=master_data['shipping_line'],
            pol=master_data['pol'],
            pod=master_data['pod'],
            client=master_data['client'],
            commodity=master_data['commodity'],
            cargo_type=Booking.CargoType.FCL,
            shipment_type='Export',
            stuffing_type='Factory',
            created_by=ops_user,
        )
        container = Container.objects.create(
            booking=booking,
            container_type=master_data['container_type'],
            container_size='20FT',
            container_count=1,
            stuffing_status='PENDING',
        )
        StockItem.objects.create(product_name='Widget', available_stock=100)

        client = _make_client(accounts_user)
        response = client.post(
            f'/api/bookings/{booking.pk}/containers/{container.pk}/stuff/',
            {'product_quantities': [{'product_name': 'Widget', 'quantity': 10}]},
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestBLEndpointRBAC:
    """Tests for Bill of Lading endpoint access control."""

    def test_accounts_user_cannot_manage_bl(self, accounts_user):
        """Accounts user is denied BL management access."""
        client = _make_client(accounts_user)
        # Attempting to list BLs via a booking that doesn't exist should still check permissions first
        response = client.post('/api/bookings/999/bl/', {}, format='json')
        # Should be 403, not 404
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_sales_user_cannot_manage_bl(self, sales_user):
        """Sales user is denied BL management access."""
        client = _make_client(sales_user)
        response = client.post('/api/bookings/999/bl/', {}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
