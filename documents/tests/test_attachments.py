"""
Tests for file attachment management (upload, list, download, delete).
"""

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from bookings.models import Booking
from documents.models import Attachment
from master_data.models import Client, Commodity, Port, ShippingLine

User = get_user_model()


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
    """Create a Sales group user (view only)."""
    user = User.objects.create_user(username='sales_user', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Sales')
    user.groups.add(group)
    return user


@pytest.fixture
def accounts_user(db):
    """Create an Accounts group user (view only)."""
    user = User.objects.create_user(username='accounts_user', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Accounts')
    user.groups.add(group)
    return user


@pytest.fixture
def master_data(db):
    """Create required master data for a booking."""
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
def booking(db, master_data, ops_user):
    """Create a test booking."""
    return Booking.objects.create(
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


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def pdf_file():
    """Create a valid small PDF file for upload."""
    return SimpleUploadedFile(
        name='test_document.pdf',
        content=b'%PDF-1.4 fake content',
        content_type='application/pdf',
    )


@pytest.fixture
def large_file():
    """Create a file exceeding 10 MB."""
    content = b'x' * (11 * 1024 * 1024)  # 11 MB
    return SimpleUploadedFile(
        name='large_file.pdf',
        content=content,
        content_type='application/pdf',
    )


@pytest.fixture
def invalid_mime_file():
    """Create a file with an invalid MIME type."""
    return SimpleUploadedFile(
        name='script.sh',
        content=b'#!/bin/bash\necho hello',
        content_type='application/x-sh',
    )


@pytest.fixture
def attachment(db, booking, ops_user):
    """Create a test attachment record."""
    return Attachment.objects.create(
        booking=booking,
        filename='existing_file.pdf',
        s3_key=f'attachments/{booking.job_number}/existing_file.pdf',
        file_size=1024,
        mime_type='application/pdf',
        uploaded_by=ops_user,
    )


@pytest.fixture
def mock_boto3():
    """Mock boto3.client to avoid real S3 calls."""
    with patch('documents.views.boto3.client') as mock_client_factory:
        mock_s3 = MagicMock()
        mock_client_factory.return_value = mock_s3
        yield mock_s3


class TestAttachmentUpload:
    """Tests for POST /api/bookings/{id}/attachments/"""

    def test_upload_valid_pdf(self, api_client, ops_user, booking, pdf_file, mock_boto3):
        """Upload a valid PDF file succeeds and stores metadata."""
        api_client.force_authenticate(user=ops_user)
        response = api_client.post(
            f'/api/bookings/{booking.pk}/attachments/',
            {'file': pdf_file},
            format='multipart',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['filename'] == 'test_document.pdf'
        assert response.data['mime_type'] == 'application/pdf'

        # Verify S3 upload was called
        mock_boto3.put_object.assert_called_once()

        # Verify metadata stored in DB
        assert Attachment.objects.filter(booking=booking).count() == 1

    def test_upload_valid_jpeg(self, api_client, ops_user, booking, mock_boto3):
        """Upload a valid JPEG image succeeds."""
        jpeg_file = SimpleUploadedFile(
            name='photo.jpeg',
            content=b'\xff\xd8\xff\xe0 fake jpeg',
            content_type='image/jpeg',
        )

        api_client.force_authenticate(user=ops_user)
        response = api_client.post(
            f'/api/bookings/{booking.pk}/attachments/',
            {'file': jpeg_file},
            format='multipart',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['mime_type'] == 'image/jpeg'

    def test_upload_valid_png(self, api_client, ops_user, booking, mock_boto3):
        """Upload a valid PNG image succeeds."""
        png_file = SimpleUploadedFile(
            name='image.png',
            content=b'\x89PNG fake content',
            content_type='image/png',
        )

        api_client.force_authenticate(user=ops_user)
        response = api_client.post(
            f'/api/bookings/{booking.pk}/attachments/',
            {'file': png_file},
            format='multipart',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['mime_type'] == 'image/png'

    def test_upload_valid_xlsx(self, api_client, ops_user, booking, mock_boto3):
        """Upload a valid XLSX file succeeds."""
        xlsx_file = SimpleUploadedFile(
            name='report.xlsx',
            content=b'PK\x03\x04 fake xlsx',
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

        api_client.force_authenticate(user=ops_user)
        response = api_client.post(
            f'/api/bookings/{booking.pk}/attachments/',
            {'file': xlsx_file},
            format='multipart',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['mime_type'] == (
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    def test_upload_valid_xls(self, api_client, ops_user, booking, mock_boto3):
        """Upload a valid XLS file succeeds."""
        xls_file = SimpleUploadedFile(
            name='report.xls',
            content=b'\xd0\xcf\x11\xe0 fake xls',
            content_type='application/vnd.ms-excel',
        )

        api_client.force_authenticate(user=ops_user)
        response = api_client.post(
            f'/api/bookings/{booking.pk}/attachments/',
            {'file': xls_file},
            format='multipart',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['mime_type'] == 'application/vnd.ms-excel'

    def test_reject_file_exceeding_10mb(self, api_client, ops_user, booking, large_file):
        """File exceeding 10 MB is rejected with 400."""
        api_client.force_authenticate(user=ops_user)
        response = api_client.post(
            f'/api/bookings/{booking.pk}/attachments/',
            {'file': large_file},
            format='multipart',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'detail' in response.data

    def test_reject_invalid_mime_type(
        self, api_client, ops_user, booking, invalid_mime_file
    ):
        """File with invalid MIME type is rejected with 400."""
        api_client.force_authenticate(user=ops_user)
        response = api_client.post(
            f'/api/bookings/{booking.pk}/attachments/',
            {'file': invalid_mime_file},
            format='multipart',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'not allowed' in response.data['detail']

    def test_enforce_max_20_attachments(
        self, api_client, ops_user, booking, pdf_file, mock_boto3
    ):
        """Cannot upload more than 20 attachments per booking."""
        # Create 20 existing attachments
        for i in range(20):
            Attachment.objects.create(
                booking=booking,
                filename=f'file_{i}.pdf',
                s3_key=f'attachments/{booking.job_number}/file_{i}.pdf',
                file_size=1024,
                mime_type='application/pdf',
                uploaded_by=ops_user,
            )

        api_client.force_authenticate(user=ops_user)
        response = api_client.post(
            f'/api/bookings/{booking.pk}/attachments/',
            {'file': pdf_file},
            format='multipart',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Maximum' in response.data['detail'] or 'maximum' in response.data['detail'].lower()

    def test_upload_to_nonexistent_booking_returns_404(
        self, api_client, ops_user, pdf_file
    ):
        """Upload to non-existent booking returns 404."""
        api_client.force_authenticate(user=ops_user)
        response = api_client.post(
            '/api/bookings/99999/attachments/',
            {'file': pdf_file},
            format='multipart',
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_s3_upload_failure_returns_500(
        self, api_client, ops_user, booking, pdf_file, mock_boto3
    ):
        """S3 upload failure returns 500."""
        mock_boto3.put_object.side_effect = ClientError(
            {'Error': {'Code': '500', 'Message': 'Internal'}}, 'PutObject'
        )

        api_client.force_authenticate(user=ops_user)
        response = api_client.post(
            f'/api/bookings/{booking.pk}/attachments/',
            {'file': pdf_file},
            format='multipart',
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestAttachmentList:
    """Tests for GET /api/bookings/{id}/attachments/"""

    def test_list_attachments(self, api_client, ops_user, booking, attachment):
        """List all attachments for a booking."""
        api_client.force_authenticate(user=ops_user)
        response = api_client.get(f'/api/bookings/{booking.pk}/attachments/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['filename'] == 'existing_file.pdf'

    def test_list_empty_attachments(self, api_client, ops_user, booking):
        """List returns empty array when no attachments exist."""
        api_client.force_authenticate(user=ops_user)
        response = api_client.get(f'/api/bookings/{booking.pk}/attachments/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0

    def test_list_for_nonexistent_booking_returns_404(self, api_client, ops_user):
        """List on non-existent booking returns 404."""
        api_client.force_authenticate(user=ops_user)
        response = api_client.get('/api/bookings/99999/attachments/')

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestAttachmentDownload:
    """Tests for GET /api/bookings/{id}/attachments/{aid}/download/"""

    def test_download_returns_presigned_url(
        self, api_client, ops_user, booking, attachment, mock_boto3
    ):
        """Download generates a pre-signed URL."""
        mock_boto3.generate_presigned_url.return_value = (
            'https://s3.amazonaws.com/bucket/attachments/1/file.pdf?signature=abc'
        )

        api_client.force_authenticate(user=ops_user)
        response = api_client.get(
            f'/api/bookings/{booking.pk}/attachments/{attachment.pk}/download/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'download_url' in response.data

        # Verify pre-signed URL generation was called with correct params
        mock_boto3.generate_presigned_url.assert_called_once_with(
            'get_object',
            Params={
                'Bucket': '',  # Empty in test settings
                'Key': attachment.s3_key,
            },
            ExpiresIn=3600,
        )

    def test_download_s3_error_returns_500(
        self, api_client, ops_user, booking, attachment, mock_boto3
    ):
        """Download returns 500 when S3 fails to generate URL."""
        mock_boto3.generate_presigned_url.side_effect = ClientError(
            {'Error': {'Code': '500', 'Message': 'Internal'}}, 'GetObject'
        )

        api_client.force_authenticate(user=ops_user)
        response = api_client.get(
            f'/api/bookings/{booking.pk}/attachments/{attachment.pk}/download/'
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_download_nonexistent_attachment_returns_404(
        self, api_client, ops_user, booking
    ):
        """Download for non-existent attachment ID returns 404."""
        api_client.force_authenticate(user=ops_user)
        response = api_client.get(
            f'/api/bookings/{booking.pk}/attachments/99999/download/'
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_download_nonexistent_booking_returns_404(
        self, api_client, ops_user, attachment
    ):
        """Download for non-existent booking returns 404."""
        api_client.force_authenticate(user=ops_user)
        response = api_client.get(
            f'/api/bookings/99999/attachments/{attachment.pk}/download/'
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestAttachmentDelete:
    """Tests for DELETE /api/bookings/{id}/attachments/{aid}/"""

    def test_delete_removes_from_s3_and_db(
        self, api_client, ops_user, booking, attachment, mock_boto3
    ):
        """Delete removes the file from S3 and deletes metadata."""
        api_client.force_authenticate(user=ops_user)
        response = api_client.delete(
            f'/api/bookings/{booking.pk}/attachments/{attachment.pk}/'
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify S3 delete was called
        mock_boto3.delete_object.assert_called_once()

        # Verify DB record removed
        assert not Attachment.objects.filter(pk=attachment.pk).exists()

    def test_delete_still_removes_db_record_on_s3_failure(
        self, api_client, ops_user, booking, attachment, mock_boto3
    ):
        """If S3 delete fails, metadata is still removed from DB."""
        mock_boto3.delete_object.side_effect = ClientError(
            {'Error': {'Code': '500', 'Message': 'Internal'}}, 'DeleteObject'
        )

        api_client.force_authenticate(user=ops_user)
        response = api_client.delete(
            f'/api/bookings/{booking.pk}/attachments/{attachment.pk}/'
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Attachment.objects.filter(pk=attachment.pk).exists()

    def test_delete_nonexistent_attachment_returns_404(
        self, api_client, ops_user, booking
    ):
        """Delete for non-existent attachment returns 404."""
        api_client.force_authenticate(user=ops_user)
        response = api_client.delete(
            f'/api/bookings/{booking.pk}/attachments/99999/'
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestAttachmentPermissions:
    """Tests for permission enforcement on attachment endpoints."""

    def test_unauthenticated_user_cannot_list(self, api_client, booking):
        """Unauthenticated user cannot list attachments."""
        response = api_client.get(f'/api/bookings/{booking.pk}/attachments/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated_user_cannot_upload(self, api_client, booking, pdf_file):
        """Unauthenticated user cannot upload attachments."""
        response = api_client.post(
            f'/api/bookings/{booking.pk}/attachments/',
            {'file': pdf_file},
            format='multipart',
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_sales_user_can_list(self, api_client, sales_user, booking, attachment):
        """Sales user (CanViewBooking) can list attachments."""
        api_client.force_authenticate(user=sales_user)
        response = api_client.get(f'/api/bookings/{booking.pk}/attachments/')
        assert response.status_code == status.HTTP_200_OK

    def test_sales_user_can_download(
        self, api_client, sales_user, booking, attachment, mock_boto3
    ):
        """Sales user (CanViewBooking) can download attachments."""
        mock_boto3.generate_presigned_url.return_value = 'https://example.com/url'

        api_client.force_authenticate(user=sales_user)
        response = api_client.get(
            f'/api/bookings/{booking.pk}/attachments/{attachment.pk}/download/'
        )
        assert response.status_code == status.HTTP_200_OK

    def test_sales_user_cannot_upload(self, api_client, sales_user, booking, pdf_file):
        """Sales user cannot upload attachments (no CanModifyBooking)."""
        api_client.force_authenticate(user=sales_user)
        response = api_client.post(
            f'/api/bookings/{booking.pk}/attachments/',
            {'file': pdf_file},
            format='multipart',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_sales_user_cannot_delete(
        self, api_client, sales_user, booking, attachment
    ):
        """Sales user cannot delete attachments (no CanModifyBooking)."""
        api_client.force_authenticate(user=sales_user)
        response = api_client.delete(
            f'/api/bookings/{booking.pk}/attachments/{attachment.pk}/'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_user_can_upload(
        self, api_client, admin_user, booking, pdf_file, mock_boto3
    ):
        """Admin user can upload attachments."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            f'/api/bookings/{booking.pk}/attachments/',
            {'file': pdf_file},
            format='multipart',
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_admin_user_can_delete(
        self, api_client, admin_user, booking, attachment, mock_boto3
    ):
        """Admin user can delete attachments."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.delete(
            f'/api/bookings/{booking.pk}/attachments/{attachment.pk}/'
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_accounts_user_can_list(
        self, api_client, accounts_user, booking, attachment
    ):
        """Accounts user (CanViewBooking) can list attachments."""
        api_client.force_authenticate(user=accounts_user)
        response = api_client.get(f'/api/bookings/{booking.pk}/attachments/')
        assert response.status_code == status.HTTP_200_OK
