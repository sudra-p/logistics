"""
Service layer for Bill of Lading operations.
"""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from bookings.models import Booking

from .models import BillOfLading


BL_TRANSITIONS = {
    'DRAFT': ['SUBMITTED'],
    'SUBMITTED': ['RELEASED'],
    'RELEASED': [],
}


class BillOfLadingService:
    """Service methods for Bill of Lading management."""

    @staticmethod
    @transaction.atomic
    def create_bl(booking_id, user, data):
        """
        Create a Bill of Lading for a booking.
        Auto-fills vessel_name, voyage_number, container_number,
        shipper, consignee, and cargo_description from booking data.
        """
        try:
            booking = Booking.objects.select_related(
                'vessel', 'shipper', 'consignee'
            ).prefetch_related('containers', 'commercial_invoices').get(pk=booking_id)
        except Booking.DoesNotExist:
            raise ValidationError({'booking_id': 'Booking not found.'})

        # Auto-fill from booking if not provided
        vessel_name = data.get('vessel_name', '')
        if not vessel_name and booking.vessel:
            vessel_name = booking.vessel.name

        voyage_number = data.get('voyage_number', '')
        if not voyage_number and booking.voyage:
            voyage_number = booking.voyage

        container_number = data.get('container_number', '')
        if not container_number:
            # Get from first container with a container_no
            container = booking.containers.filter(
                container_no__gt=''
            ).first()
            if container:
                container_number = container.container_no

        shipper = data.get('shipper')
        if not shipper and booking.shipper:
            shipper = booking.shipper

        consignee = data.get('consignee')
        if not consignee and booking.consignee:
            consignee = booking.consignee

        cargo_description = data.get('cargo_description', '')
        if not cargo_description:
            # Auto-fill from Commercial Invoice line items
            latest_invoice = booking.commercial_invoices.order_by('-revision').first()
            if latest_invoice:
                items = latest_invoice.line_items.all()
                descriptions = [item.product_name for item in items]
                cargo_description = ', '.join(descriptions)

        if not shipper:
            raise ValidationError({'shipper': 'Shipper is required.'})
        if not consignee:
            raise ValidationError({'consignee': 'Consignee is required.'})

        bl = BillOfLading.objects.create(
            booking=booking,
            bl_number=data['bl_number'],
            bl_type=data['bl_type'],
            container_number=container_number,
            vessel_name=vessel_name,
            voyage_number=voyage_number,
            shipper=shipper,
            consignee=consignee,
            notify_party=data.get('notify_party', ''),
            cargo_description=cargo_description,
            created_by=user,
        )

        return bl

    @staticmethod
    @transaction.atomic
    def change_bl_status(bl_id, new_status, user):
        """
        Change BL status with transition validation.
        DRAFT → SUBMITTED → RELEASED
        """
        try:
            bl = BillOfLading.objects.get(pk=bl_id)
        except BillOfLading.DoesNotExist:
            raise ValidationError({'id': 'Bill of Lading not found.'})

        current_status = bl.status
        allowed = BL_TRANSITIONS.get(current_status, [])

        if new_status not in allowed:
            raise ValidationError({
                'status': (
                    f'Cannot transition from {current_status} to {new_status}. '
                    f'Allowed transitions: {allowed}'
                )
            })

        bl.status = new_status
        bl.save()
        return bl

    @staticmethod
    @transaction.atomic
    def update_bl(bl_id, user, data):
        """Update a Bill of Lading. Only DRAFT BLs can be modified."""
        try:
            bl = BillOfLading.objects.get(pk=bl_id)
        except BillOfLading.DoesNotExist:
            raise ValidationError({'id': 'Bill of Lading not found.'})

        if bl.status != BillOfLading.Status.DRAFT:
            raise ValidationError(
                {'status': 'Only DRAFT Bills of Lading can be edited.'}
            )

        # Update fields
        for field, value in data.items():
            if hasattr(bl, field) and field not in ('id', 'bl_number', 'booking', 'created_by', 'created_at'):
                setattr(bl, field, value)

        bl.save()
        return bl
