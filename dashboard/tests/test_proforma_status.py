"""
Tests for the dashboard proforma-status endpoint.
"""

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APIClient

from master_data.models import Client
from proforma.models import ProformaInvoice

User = get_user_model()

PROFORMA_STATUS_URL = '/api/dashboard/proforma-status/'


@pytest.fixture
def authenticated_client(db):
    """Create an authenticated user and API client."""
    user = User.objects.create_user(username='testuser', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Operations')
    user.groups.add(group)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def test_client_entity(db):
    """Create a Client master data record."""
    return Client.objects.create(name='Acme Corp', email='acme@test.com')


class TestProformaStatusEndpoint:
    """Tests for GET /api/dashboard/proforma-status/"""

    def test_unauthenticated_returns_401(self, db):
        client = APIClient()
        response = client.get(PROFORMA_STATUS_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_database_returns_empty_list(self, authenticated_client):
        client, user = authenticated_client
        response = client.get(PROFORMA_STATUS_URL)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['results'] == []
        assert data['count'] == 0

    def test_excludes_paid_proformas(self, authenticated_client, test_client_entity):
        client, user = authenticated_client
        # Create a PAID PI — should be excluded
        ProformaInvoice.objects.create(
            date=datetime.date.today(),
            customer=test_client_entity,
            currency='USD',
            payment_terms='Net 30',
            expected_shipment_date=datetime.date.today(),
            status=ProformaInvoice.Status.PAID,
            created_by=user,
        )
        response = client.get(PROFORMA_STATUS_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()['count'] == 0

    def test_includes_non_paid_proformas(self, authenticated_client, test_client_entity):
        client, user = authenticated_client
        non_paid_statuses = [
            ProformaInvoice.Status.DRAFT,
            ProformaInvoice.Status.SENT,
            ProformaInvoice.Status.APPROVED,
            ProformaInvoice.Status.PAYMENT_PENDING,
        ]
        for s in non_paid_statuses:
            ProformaInvoice.objects.create(
                date=datetime.date.today(),
                customer=test_client_entity,
                currency='USD',
                payment_terms='Net 30',
                expected_shipment_date=datetime.date.today(),
                status=s,
                created_by=user,
            )
        response = client.get(PROFORMA_STATUS_URL)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['count'] == 4

    def test_response_fields(self, authenticated_client, test_client_entity):
        client, user = authenticated_client
        ProformaInvoice.objects.create(
            date=datetime.date.today(),
            customer=test_client_entity,
            currency='USD',
            payment_terms='Net 30',
            expected_shipment_date=datetime.date.today(),
            total_amount=Decimal('5000.00'),
            status=ProformaInvoice.Status.DRAFT,
            created_by=user,
        )
        response = client.get(PROFORMA_STATUS_URL)
        assert response.status_code == status.HTTP_200_OK
        result = response.json()['results'][0]
        assert 'pi_number' in result
        assert result['customer_name'] == 'Acme Corp'
        assert result['amount'] == '5000.00'
        assert result['status'] == 'DRAFT'

    def test_pagination(self, authenticated_client, test_client_entity):
        client, user = authenticated_client
        # Create 30 PIs (default page_size is 25)
        for i in range(30):
            ProformaInvoice.objects.create(
                date=datetime.date.today(),
                customer=test_client_entity,
                currency='USD',
                payment_terms='Net 30',
                expected_shipment_date=datetime.date.today(),
                status=ProformaInvoice.Status.DRAFT,
                created_by=user,
            )
        response = client.get(PROFORMA_STATUS_URL)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['count'] == 30
        assert len(data['results']) == 25
        assert data['next'] is not None

    def test_custom_page_size(self, authenticated_client, test_client_entity):
        client, user = authenticated_client
        for i in range(10):
            ProformaInvoice.objects.create(
                date=datetime.date.today(),
                customer=test_client_entity,
                currency='USD',
                payment_terms='Net 30',
                expected_shipment_date=datetime.date.today(),
                status=ProformaInvoice.Status.DRAFT,
                created_by=user,
            )
        response = client.get(PROFORMA_STATUS_URL + '?page_size=5')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['count'] == 10
        assert len(data['results']) == 5
