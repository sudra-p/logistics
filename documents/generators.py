"""
PDF document generation for DO and BL drafts.

Uses WeasyPrint for HTML-to-PDF conversion and boto3 for S3 upload.
"""

import logging
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.template.loader import render_to_string
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)


class PDFGenerationError(Exception):
    """Raised when PDF generation or upload fails."""

    pass


class PDFGenerator:
    """Generates PDF documents for DO and BL drafts."""

    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION,
        )
        self.bucket_name = settings.AWS_S3_BUCKET_NAME

    def _validate_do_fields(self, booking):
        """
        Validate that all required fields for DO draft are present.
        Returns a list of missing field names.
        """
        missing = []

        if not booking.job_number:
            missing.append('job_number')
        if not booking.shipper:
            missing.append('shipper')
        if not booking.consignee:
            missing.append('consignee')
        if not booking.vessel:
            missing.append('vessel')
        if not booking.voyage:
            missing.append('voyage')
        if not booking.pol:
            missing.append('pol')
        if not booking.pod:
            missing.append('pod')
        if not booking.containers.exists():
            missing.append('containers')

        return missing

    def _validate_bl_fields(self, booking):
        """
        Validate that all required fields for BL draft are present.
        Returns a list of missing field names.
        """
        missing = []

        if not booking.shipper:
            missing.append('shipper')
        elif not booking.shipper.name:
            missing.append('shipper_name')
        if booking.shipper and not booking.shipper.address:
            missing.append('shipper_address')

        if not booking.consignee:
            missing.append('consignee')
        elif not booking.consignee.name:
            missing.append('consignee_name')
        if booking.consignee and not booking.consignee.address:
            missing.append('consignee_address')

        if not booking.vessel:
            missing.append('vessel')
        if not booking.voyage:
            missing.append('voyage')
        if not booking.pol:
            missing.append('pol')
        if not booking.pod:
            missing.append('pod')
        if not booking.fpd:
            missing.append('fpd')
        if not booking.containers.exists():
            missing.append('containers')
        if not booking.hbl_freight_terms and not booking.mbl_freight_terms:
            missing.append('freight_terms')

        return missing

    def _render_pdf(self, template_name, context):
        """Render HTML template to PDF bytes."""
        from weasyprint import HTML

        html_string = render_to_string(template_name, context)
        pdf_bytes = HTML(string=html_string).write_pdf()
        return pdf_bytes

    def _upload_to_s3(self, pdf_bytes, s3_key):
        """
        Upload PDF bytes to S3 and return a pre-signed download URL.
        Raises PDFGenerationError if upload fails.
        """
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=pdf_bytes,
                ContentType='application/pdf',
            )
        except ClientError as e:
            logger.error(f"S3 upload failed for key {s3_key}: {e}")
            raise PDFGenerationError(
                f"Failed to upload document to storage: {e}"
            )

        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key,
                },
                ExpiresIn=settings.AWS_S3_PRESIGNED_URL_EXPIRY,
            )
        except ClientError as e:
            logger.error(f"Failed to generate pre-signed URL for {s3_key}: {e}")
            raise PDFGenerationError(
                f"Failed to generate download URL: {e}"
            )

        return url

    def generate_do_draft(self, booking):
        """
        Generate a Delivery Order draft PDF for the given booking.

        Validates required fields, renders the PDF from template,
        uploads to S3, and returns a pre-signed download URL (60 min expiry).

        Raises:
            ValidationError: If required fields are missing.
            PDFGenerationError: If PDF generation or S3 upload fails.
        """
        missing = self._validate_do_fields(booking)
        if missing:
            raise ValidationError({
                'missing_fields': missing,
                'detail': f"Cannot generate DO draft. Missing required fields: {', '.join(missing)}",
            })

        context = {
            'booking': booking,
            'containers': booking.containers.all(),
            'generated_at': datetime.now(timezone.utc),
        }

        pdf_bytes = self._render_pdf('documents/do_draft.html', context)

        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        s3_key = f"documents/do-drafts/{booking.job_number}_{timestamp}.pdf"

        url = self._upload_to_s3(pdf_bytes, s3_key)
        return url

    def generate_bl_draft(self, booking):
        """
        Generate a Bill of Lading draft PDF for the given booking.

        Validates required fields, renders the PDF from template,
        uploads to S3, and returns a pre-signed download URL (60 min expiry).

        Raises:
            ValidationError: If required fields are missing.
            PDFGenerationError: If PDF generation or S3 upload fails.
        """
        missing = self._validate_bl_fields(booking)
        if missing:
            raise ValidationError({
                'missing_fields': missing,
                'detail': f"Cannot generate BL draft. Missing required fields: {', '.join(missing)}",
            })

        context = {
            'booking': booking,
            'containers': booking.containers.all(),
            'generated_at': datetime.now(timezone.utc),
        }

        pdf_bytes = self._render_pdf('documents/bl_draft.html', context)

        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        s3_key = f"documents/bl-drafts/{booking.job_number}_{timestamp}.pdf"

        url = self._upload_to_s3(pdf_bytes, s3_key)
        return url
