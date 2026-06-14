"""
Tests for DO and BL draft PDF generation.
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APIClient

from bookings.models import Booking, Container
from documents.generators import PDFGenerationError, PDFGenerator
from master_data.models import (
    Client,
    Commodity,
    Consignee,
    ContainerType,
    Port,
    Shipper,
    ShippingLine,
    Vessel,
)

User = get_user_model()


@pytest.fixture
def operations_user(db):
    """Create an Operations group user."""
    user = User.objects.create_user(username='ops_user', password='testpass')
    group, _ = Group.objects.get_or_create(name='Operations')
    user.groups.add(group)
    return user


@pytest.fixture
def sales_user(db):
    """Create a Sales group user (no modify permission)."""
    user = User.objects.create_user(username='sales_user', password='testpass')
    group, _ = Group.objects.get_or_create(name='Sales')
    user.groups.add(group)
    return user


@pytest.fixture
def master_data(db):
    """Create required master data for bookings."""
    shipping_line = ShippingLine.objects.create(name='Maersk', code='MAEU')
    pol = Port.objects.create(name='Mumbai', code='INMUN', country='India')
    pod = Port.objects.create(name='Rotterdam', code='NLRTM', country='Netherlands')
    fpd = Port.objects.create(name='Hamburg', code='DEHAM', country='Germany')
    client = Client.objects.create(name='Test Client', email='client@test.com')
    commodity = Commodity.objects.create(name='Electronics', hs_code='8471')
    vessel = Vessel.objects.create(name='MSC Arina', imo_number='1234567')
    shipper = Shipper.objects.create(name='Test Shipper', address='123 Ship St')
    consignee = Consignee.objects.create(name='Test Consignee', address='456 Con Ave')
    container_type = ContainerType.objects.create(name='Dry', code='DRY')
    return {
        'shipping_line': shipping_line,
        'pol': pol,
        'pod': pod,
        'fpd': fpd,
        'client': client,
        'commodity': commodity,
        'vessel': vessel,
        'shipper': shipper,
        'consignee': consignee,
        'container_type': container_type,
    }


@pytest.fixture
def complete_booking(db, operations_user, master_data):
    """Create a booking with all required fields for DO/BL generation."""
    booking = Booking.objects.create(
        booking_date=date(2024, 1, 15),
        booking_validity_date=date(2024, 2, 15),
        forwarding_window_start=date(2024, 1, 20),
        forwarding_window_end=date(2024, 2, 10),
        shipping_line=master_data['shipping_line'],
        pol=master_data['pol'],
        pod=master_data['pod'],
        fpd=master_data['fpd'],
        client=master_data['client'],
        commodity=master_data['commodity'],
        cargo_type='FCL',
        shipment_type='Direct',
        stuffing_type='Factory',
        vessel=master_data['vessel'],
        voyage='V123E',
        shipper=master_data['shipper'],
        consignee=master_data['consignee'],
        hbl_freight_terms='PREPAID',
        created_by=operations_user,
    )
    Container.objects.create(
        booking=booking,
        container_type=master_data['container_type'],
        container_size='20FT',
        container_count=2,
    )
    return booking


@pytest.fixture
def incomplete_booking(db, operations_user, master_data):
    """Create a booking missing some fields required for DO/BL generation."""
    booking = Booking.objects.create(
        booking_date=date(2024, 1, 15),
        booking_validity_date=date(2024, 2, 15),
        forwarding_window_start=date(2024, 1, 20),
        forwarding_window_end=date(2024, 2, 10),
        shipping_line=master_data['shipping_line'],
        pol=master_data['pol'],
        pod=master_data['pod'],
        client=master_data['client'],
        commodity=master_data['commodity'],
        cargo_type='FCL',
        shipment_type='Direct',
        stuffing_type='Factory',
        created_by=operations_user,
        # Missing: vessel, voyage, shipper, consignee, containers
    )
    return booking


@pytest.fixture
def api_client(operations_user):
    """Authenticated API client with Operations permissions."""
    client = APIClient()
    client.force_authenticate(user=operations_user)
    return client


@pytest.fixture
def sales_api_client(sales_user):
    """Authenticated API client with only Sales permissions."""
    client = APIClient()
    client.force_authenticate(user=sales_user)
    return client


# ---------------------------------------------------------------------------
# Unit Tests for PDFGenerator
# ---------------------------------------------------------------------------


class TestDODraftValidation:
    """Tests for DO draft field validation."""

    def test_validate_do_fields_all_present(self, complete_booking):
        """All required fields present returns no missing fields."""
        generator = PDFGenerator.__new__(PDFGenerator)
        missing = generator._validate_do_fields(complete_booking)
        assert missing == []

    def test_validate_do_fields_missing_shipper_consignee(self, incomplete_booking):
        """Missing shipper and consignee are reported."""
        generator = PDFGenerator.__new__(PDFGenerator)
        missing = generator._validate_do_fields(incomplete_booking)
        assert 'shipper' in missing
        assert 'consignee' in missing

    def test_validate_do_fields_missing_vessel_voyage(self, incomplete_booking):
        """Missing vessel and voyage are reported."""
        generator = PDFGenerator.__new__(PDFGenerator)
        missing = generator._validate_do_fields(incomplete_booking)
        assert 'vessel' in missing
        assert 'voyage' in missing

    def test_validate_do_fields_missing_containers(self, incomplete_booking):
        """Missing containers are reported."""
        generator = PDFGenerator.__new__(PDFGenerator)
        missing = generator._validate_do_fields(incomplete_booking)
        assert 'containers' in missing


class TestBLDraftValidation:
    """Tests for BL draft field validation."""

    def test_validate_bl_fields_all_present(self, complete_booking):
        """All required fields present returns no missing fields."""
        generator = PDFGenerator.__new__(PDFGenerator)
        missing = generator._validate_bl_fields(complete_booking)
        assert missing == []

    def test_validate_bl_fields_missing_fpd(self, incomplete_booking):
        """Missing FPD is reported."""
        generator = PDFGenerator.__new__(PDFGenerator)
        missing = generator._validate_bl_fields(incomplete_booking)
        assert 'fpd' in missing

    def test_validate_bl_fields_missing_freight_terms(self, incomplete_booking):
        """Missing freight terms are reported."""
        generator = PDFGenerator.__new__(PDFGenerator)
        missing = generator._validate_bl_fields(incomplete_booking)
        assert 'freight_terms' in missing


# ---------------------------------------------------------------------------
# Integration Tests for DO/BL Draft Endpoints
# ---------------------------------------------------------------------------


class TestDODraftEndpoint:
    """Tests for POST /api/bookings/{id}/documents/do-draft/."""

    @patch('documents.generators.PDFGenerator._render_pdf', return_value=b'%PDF-fake-content')
    @patch('documents.generators.boto3.client')
    def test_successful_do_draft_generation(
        self, mock_boto_client, mock_render_pdf, api_client, complete_booking
    ):
        """Successful DO draft generation returns download URL."""
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = (
            'https://s3.amazonaws.com/test-bucket/documents/do-drafts/test.pdf?sig=abc'
        )
        mock_boto_client.return_value = mock_s3

        response = api_client.post(
            f'/api/bookings/{complete_booking.pk}/documents/do-draft/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'download_url' in response.data
        assert response.data['download_url'].startswith('https://')
        mock_s3.put_object.assert_called_once()

    @patch('documents.generators.boto3.client')
    def test_do_draft_missing_fields_returns_400(
        self, mock_boto_client, api_client, incomplete_booking
    ):
        """Missing required fields returns 400 with field names."""
        response = api_client.post(
            f'/api/bookings/{incomplete_booking.pk}/documents/do-draft/'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'missing_fields' in response.data
        assert 'shipper' in response.data['missing_fields']
        assert 'vessel' in response.data['missing_fields']

    def test_do_draft_booking_not_found(self, api_client):
        """Non-existent booking returns 404."""
        response = api_client.post('/api/bookings/99999/documents/do-draft/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch('documents.generators.PDFGenerator._render_pdf', return_value=b'%PDF-fake')
    @patch('documents.generators.boto3.client')
    def test_do_draft_s3_upload_failure(
        self, mock_boto_client, mock_render_pdf, api_client, complete_booking
    ):
        """S3 upload failure returns 500."""
        from botocore.exceptions import ClientError

        mock_s3 = MagicMock()
        mock_s3.put_object.side_effect = ClientError(
            {'Error': {'Code': 'InternalError', 'Message': 'S3 failure'}},
            'PutObject',
        )
        mock_boto_client.return_value = mock_s3

        response = api_client.post(
            f'/api/bookings/{complete_booking.pk}/documents/do-draft/'
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert 'detail' in response.data

    def test_do_draft_permission_denied(self, sales_api_client, complete_booking):
        """Sales user cannot generate DO draft."""
        response = sales_api_client.post(
            f'/api/bookings/{complete_booking.pk}/documents/do-draft/'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestBLDraftEndpoint:
    """Tests for POST /api/bookings/{id}/documents/bl-draft/."""

    @patch('documents.generators.PDFGenerator._render_pdf', return_value=b'%PDF-fake-content')
    @patch('documents.generators.boto3.client')
    def test_successful_bl_draft_generation(
        self, mock_boto_client, mock_render_pdf, api_client, complete_booking
    ):
        """Successful BL draft generation returns download URL."""
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = (
            'https://s3.amazonaws.com/test-bucket/documents/bl-drafts/test.pdf?sig=abc'
        )
        mock_boto_client.return_value = mock_s3

        response = api_client.post(
            f'/api/bookings/{complete_booking.pk}/documents/bl-draft/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'download_url' in response.data
        assert response.data['download_url'].startswith('https://')

    @patch('documents.generators.boto3.client')
    def test_bl_draft_missing_fields_returns_400(
        self, mock_boto_client, api_client, incomplete_booking
    ):
        """Missing required fields returns 400 with field names."""
        response = api_client.post(
            f'/api/bookings/{incomplete_booking.pk}/documents/bl-draft/'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'missing_fields' in response.data
        assert 'fpd' in response.data['missing_fields']
        assert 'freight_terms' in response.data['missing_fields']

    def test_bl_draft_booking_not_found(self, api_client):
        """Non-existent booking returns 404."""
        response = api_client.post('/api/bookings/99999/documents/bl-draft/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch('documents.generators.PDFGenerator._render_pdf', return_value=b'%PDF-fake')
    @patch('documents.generators.boto3.client')
    def test_bl_draft_s3_upload_failure(
        self, mock_boto_client, mock_render_pdf, api_client, complete_booking
    ):
        """S3 upload failure returns 500."""
        from botocore.exceptions import ClientError

        mock_s3 = MagicMock()
        mock_s3.put_object.side_effect = ClientError(
            {'Error': {'Code': 'InternalError', 'Message': 'S3 failure'}},
            'PutObject',
        )
        mock_boto_client.return_value = mock_s3

        response = api_client.post(
            f'/api/bookings/{complete_booking.pk}/documents/bl-draft/'
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert 'detail' in response.data

    def test_bl_draft_permission_denied(self, sales_api_client, complete_booking):
        """Sales user cannot generate BL draft."""
        response = sales_api_client.post(
            f'/api/bookings/{complete_booking.pk}/documents/bl-draft/'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
