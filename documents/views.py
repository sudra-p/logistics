"""
Views for document generation and attachment management endpoints.
"""

import logging

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import CanModifyBooking, CanViewBooking
from bookings.models import Booking
from documents.generators import PDFGenerationError, PDFGenerator
from documents.models import Attachment

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PDF Draft Generation Views
# ---------------------------------------------------------------------------


class DODraftView(APIView):
    """
    POST /api/bookings/{booking_id}/documents/do-draft/

    Generate a Delivery Order draft PDF for the specified booking.
    Returns a pre-signed S3 URL for downloading the generated PDF.
    """

    permission_classes = [CanModifyBooking]

    def post(self, request, booking_id):
        try:
            booking = Booking.objects.select_related(
                'shipper', 'consignee', 'vessel', 'pol', 'pod'
            ).prefetch_related('containers').get(pk=booking_id)
        except Booking.DoesNotExist:
            return Response(
                {'detail': 'Booking not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        generator = PDFGenerator()
        try:
            url = generator.generate_do_draft(booking)
        except PDFGenerationError as e:
            logger.error(f"DO draft generation failed for booking {booking_id}: {e}")
            return Response(
                {'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({'download_url': url}, status=status.HTTP_200_OK)


class BLDraftView(APIView):
    """
    POST /api/bookings/{booking_id}/documents/bl-draft/

    Generate a Bill of Lading draft PDF for the specified booking.
    Returns a pre-signed S3 URL for downloading the generated PDF.
    """

    permission_classes = [CanModifyBooking]

    def post(self, request, booking_id):
        try:
            booking = Booking.objects.select_related(
                'shipper', 'consignee', 'vessel', 'pol', 'pod', 'fpd'
            ).prefetch_related('containers').get(pk=booking_id)
        except Booking.DoesNotExist:
            return Response(
                {'detail': 'Booking not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        generator = PDFGenerator()
        try:
            url = generator.generate_bl_draft(booking)
        except PDFGenerationError as e:
            logger.error(f"BL draft generation failed for booking {booking_id}: {e}")
            return Response(
                {'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({'download_url': url}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Attachment Views
# ---------------------------------------------------------------------------


class AttachmentListCreateView(APIView):
    """
    GET  /api/bookings/{booking_id}/attachments/ — list attachments
    POST /api/bookings/{booking_id}/attachments/ — upload an attachment
    """

    parser_classes = [MultiPartParser]

    def get_permissions(self):
        if self.request.method == 'GET':
            return [CanViewBooking()]
        return [CanModifyBooking()]

    def get(self, request, booking_id):
        try:
            booking = Booking.objects.get(pk=booking_id)
        except Booking.DoesNotExist:
            return Response(
                {'detail': 'Booking not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        attachments = booking.attachments.all()
        data = [
            {
                'id': a.id,
                'filename': a.filename,
                'file_size': a.file_size,
                'mime_type': a.mime_type,
                'uploaded_at': a.uploaded_at.isoformat(),
            }
            for a in attachments
        ]
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request, booking_id):
        try:
            booking = Booking.objects.get(pk=booking_id)
        except Booking.DoesNotExist:
            return Response(
                {'detail': 'Booking not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        file = request.FILES.get('file')
        if not file:
            return Response(
                {'detail': 'No file provided.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if file.content_type not in Attachment.ALLOWED_MIME_TYPES:
            return Response(
                {'detail': f'File type {file.content_type} is not allowed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if file.size > Attachment.MAX_FILE_SIZE:
            return Response(
                {'detail': 'File exceeds maximum size of 10 MB.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if booking.attachments.count() >= Attachment.MAX_ATTACHMENTS_PER_BOOKING:
            return Response(
                {'detail': 'Maximum number of attachments reached.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        s3_key = f"attachments/{booking.job_number}/{file.name}"
        try:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION,
            )
            s3_client.put_object(
                Bucket=settings.AWS_S3_BUCKET_NAME,
                Key=s3_key,
                Body=file.read(),
                ContentType=file.content_type,
            )
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            return Response(
                {'detail': 'Failed to upload file.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        attachment = Attachment.objects.create(
            booking=booking,
            filename=file.name,
            s3_key=s3_key,
            file_size=file.size,
            mime_type=file.content_type,
            uploaded_by=request.user,
        )

        return Response(
            {
                'id': attachment.id,
                'filename': attachment.filename,
                'file_size': attachment.file_size,
                'mime_type': attachment.mime_type,
                'uploaded_at': attachment.uploaded_at.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )


class AttachmentDownloadView(APIView):
    """
    GET /api/bookings/{booking_id}/attachments/{attachment_id}/download/
    """

    permission_classes = [CanViewBooking]

    def get(self, request, booking_id, attachment_id):
        try:
            attachment = Attachment.objects.get(
                pk=attachment_id, booking_id=booking_id
            )
        except Attachment.DoesNotExist:
            return Response(
                {'detail': 'Attachment not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION,
            )
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.AWS_S3_BUCKET_NAME,
                    'Key': attachment.s3_key,
                },
                ExpiresIn=settings.AWS_S3_PRESIGNED_URL_EXPIRY,
            )
        except ClientError as e:
            logger.error(f"Failed to generate download URL: {e}")
            return Response(
                {'detail': 'Failed to generate download URL.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({'download_url': url}, status=status.HTTP_200_OK)


class AttachmentDeleteView(APIView):
    """
    DELETE /api/bookings/{booking_id}/attachments/{attachment_id}/
    """

    permission_classes = [CanModifyBooking]

    def delete(self, request, booking_id, attachment_id):
        try:
            attachment = Attachment.objects.get(
                pk=attachment_id, booking_id=booking_id
            )
        except Attachment.DoesNotExist:
            return Response(
                {'detail': 'Attachment not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION,
            )
            s3_client.delete_object(
                Bucket=settings.AWS_S3_BUCKET_NAME,
                Key=attachment.s3_key,
            )
        except ClientError as e:
            logger.error(f"S3 delete failed: {e}")

        attachment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
