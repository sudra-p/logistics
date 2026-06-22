"""
Business logic service layer for Proforma Invoice operations.
"""

from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers

from bookings.models import Booking
from proforma.models import ProformaInvoice, ProformaLineItem


# Valid PI status transitions
PI_TRANSITIONS = {
    'DRAFT': ['SENT'],
    'SENT': ['APPROVED'],
    'APPROVED': ['PAYMENT_PENDING'],
    'PAYMENT_PENDING': ['PAID'],
    'PAID': [],
}


class ProformaService:
    """Service class encapsulating Proforma Invoice business logic."""

    @staticmethod
    @transaction.atomic
    def create_proforma(data, user):
        """
        Create a Proforma Invoice with line items in a transaction.
        Computes total_amount from line items.

        Args:
            data: Dict of validated fields from ProformaInvoiceCreateSerializer.
            user: The authenticated user creating the PI.

        Returns:
            The created ProformaInvoice instance.
        """
        line_items_data = data.pop('line_items')

        pi = ProformaInvoice(
            created_by=user,
            **data,
        )
        pi.save()

        # Create line items
        total = Decimal('0.00')
        for item_data in line_items_data:
            line_item = ProformaLineItem(
                proforma_invoice=pi,
                **item_data,
            )
            line_item.save()
            total += line_item.amount

        # Update total_amount
        pi.total_amount = total
        pi.save(update_fields=['total_amount'])

        return pi

    @staticmethod
    @transaction.atomic
    def update_proforma(pi_id, data, user):
        """
        Update a Proforma Invoice and replace line items if provided.

        Args:
            pi_id: ID of the ProformaInvoice to update.
            data: Dict of validated fields from ProformaInvoiceUpdateSerializer.
            user: The authenticated user performing the update.

        Returns:
            The updated ProformaInvoice instance.

        Raises:
            Http404 if PI not found.
            serializers.ValidationError if PI is not in DRAFT status.
        """
        pi = get_object_or_404(ProformaInvoice, pk=pi_id)

        if pi.status != ProformaInvoice.Status.DRAFT:
            raise serializers.ValidationError({
                'detail': 'Can only update Proforma Invoices in DRAFT status.'
            })

        line_items_data = data.pop('line_items', None)

        # Update scalar fields
        for field, value in data.items():
            setattr(pi, field, value)
        pi.save()

        # Replace line items if provided
        if line_items_data is not None:
            pi.line_items.all().delete()

            total = Decimal('0.00')
            for item_data in line_items_data:
                line_item = ProformaLineItem(
                    proforma_invoice=pi,
                    **item_data,
                )
                line_item.save()
                total += line_item.amount

            pi.total_amount = total
            pi.save(update_fields=['total_amount'])

        return pi

    @staticmethod
    def change_status(pi_id, new_status, user):
        """
        Validate and perform a status transition on a Proforma Invoice.

        Allowed transitions: DRAFT → SENT → APPROVED → PAYMENT_PENDING → PAID

        Args:
            pi_id: ID of the ProformaInvoice.
            new_status: The target status string.
            user: The authenticated user performing the change.

        Returns:
            The updated ProformaInvoice instance.

        Raises:
            Http404 if PI not found.
            serializers.ValidationError if transition is invalid.
        """
        pi = get_object_or_404(ProformaInvoice, pk=pi_id)

        current_status = pi.status
        allowed = PI_TRANSITIONS.get(current_status, [])

        if new_status not in allowed:
            if allowed:
                raise serializers.ValidationError({
                    'status': (
                        f'Cannot transition from {current_status} to {new_status}. '
                        f'Allowed transitions: {allowed}.'
                    )
                })
            else:
                raise serializers.ValidationError({
                    'status': (
                        f'Cannot transition from {current_status}. '
                        f'It is a terminal status.'
                    )
                })

        pi.status = new_status
        pi.save(update_fields=['status'])

        return pi


@transaction.atomic
def auto_create_booking(pi_id, user, **booking_data):
    """
    Auto-create a Booking pre-filled with data from a Proforma Invoice.

    Validates that the PI is in PAID status, then creates a Booking with:
    - client from PI.customer
    - booking_date and forwarding window dates from PI.expected_shipment_date
    - proforma_invoice linked to the PI
    - status set to PENDING

    Any additional required booking fields (e.g. shipping_line, pol, pod,
    commodity, cargo_type, shipment_type, stuffing_type) can be passed via
    booking_data keyword arguments.

    Args:
        pi_id: ID of the ProformaInvoice to create a booking from.
        user: The authenticated user triggering the auto-creation.
        **booking_data: Additional Booking field values to set on the new
            booking (overrides pre-filled values if provided).

    Returns:
        The created Booking instance.

    Raises:
        Http404 if PI not found.
        serializers.ValidationError if PI is not in PAID status.
    """
    pi = get_object_or_404(ProformaInvoice, pk=pi_id)

    if pi.status != ProformaInvoice.Status.PAID:
        raise serializers.ValidationError({
            'detail': (
                'Cannot auto-create booking. '
                'Proforma Invoice must be in PAID status.'
            )
        })

    # Pre-fill fields from the Proforma Invoice
    defaults = {
        'client': pi.customer,
        'proforma_invoice': pi,
        'booking_date': pi.expected_shipment_date,
        'booking_validity_date': pi.expected_shipment_date,
        'forwarding_window_start': pi.expected_shipment_date,
        'forwarding_window_end': pi.expected_shipment_date,
        'status': Booking.Status.PENDING,
        'created_by': user,
    }

    # Allow caller to override or supply additional fields
    defaults.update(booking_data)

    booking = Booking(**defaults)
    booking.save()

    return booking
