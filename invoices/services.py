"""
Service layer for Commercial Invoice and Packing List operations.
"""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from bookings.models import Booking

from .models import (
    CommercialInvoice,
    CommercialInvoiceLineItem,
    PackingList,
    PackingListLineItem,
)


class CommercialInvoiceService:
    """Service methods for Commercial Invoice management."""

    @staticmethod
    @transaction.atomic
    def create_commercial_invoice(booking_id, user, line_items=None):
        """
        Create a Commercial Invoice for a booking.
        Auto-fills line items from the linked Proforma Invoice if no line_items provided.
        """
        try:
            booking = Booking.objects.get(pk=booking_id)
        except Booking.DoesNotExist:
            raise ValidationError({'booking_id': 'Booking not found.'})

        invoice = CommercialInvoice.objects.create(
            booking=booking,
            created_by=user,
        )

        if line_items:
            # Use provided line items
            for item_data in line_items:
                CommercialInvoiceLineItem.objects.create(
                    commercial_invoice=invoice,
                    **item_data,
                )
        else:
            # Auto-fill from linked Proforma Invoice
            pi = booking.proforma_invoice
            if pi:
                for pi_item in pi.line_items.all():
                    CommercialInvoiceLineItem.objects.create(
                        commercial_invoice=invoice,
                        product_name=pi_item.product_name,
                        quantity=pi_item.quantity,
                        rate=pi_item.rate,
                        amount=pi_item.amount,
                    )

        return invoice

    @staticmethod
    @transaction.atomic
    def finalize_invoice(invoice_id, user):
        """Finalize a Commercial Invoice (set status to FINALIZED)."""
        try:
            invoice = CommercialInvoice.objects.get(pk=invoice_id)
        except CommercialInvoice.DoesNotExist:
            raise ValidationError({'id': 'Commercial Invoice not found.'})

        if invoice.status == CommercialInvoice.Status.FINALIZED:
            raise ValidationError(
                {'status': 'Invoice is already finalized.'}
            )

        invoice.status = CommercialInvoice.Status.FINALIZED
        invoice.save()
        return invoice

    @staticmethod
    @transaction.atomic
    def create_revision(invoice_id, user):
        """
        Create a new revision of a finalized Commercial Invoice.
        Creates a new DRAFT invoice with revision + 1, copying line items.
        """
        try:
            invoice = CommercialInvoice.objects.get(pk=invoice_id)
        except CommercialInvoice.DoesNotExist:
            raise ValidationError({'id': 'Commercial Invoice not found.'})

        if invoice.status != CommercialInvoice.Status.FINALIZED:
            raise ValidationError(
                {'status': 'Only finalized invoices can be revised.'}
            )

        new_invoice = CommercialInvoice.objects.create(
            booking=invoice.booking,
            revision=invoice.revision + 1,
            created_by=user,
        )

        # Copy line items from the previous revision
        for item in invoice.line_items.all():
            CommercialInvoiceLineItem.objects.create(
                commercial_invoice=new_invoice,
                product_name=item.product_name,
                quantity=item.quantity,
                rate=item.rate,
                amount=item.amount,
                net_weight=item.net_weight,
                gross_weight=item.gross_weight,
                hs_code=item.hs_code,
                num_packages=item.num_packages,
            )

        return new_invoice

    @staticmethod
    @transaction.atomic
    def update_invoice(invoice_id, user, line_items=None):
        """Update a Commercial Invoice's line items. Prevents edits to finalized docs."""
        try:
            invoice = CommercialInvoice.objects.get(pk=invoice_id)
        except CommercialInvoice.DoesNotExist:
            raise ValidationError({'id': 'Commercial Invoice not found.'})

        if invoice.status == CommercialInvoice.Status.FINALIZED:
            raise ValidationError(
                {'status': 'Cannot edit a finalized invoice. Create a new revision instead.'}
            )

        if line_items is not None:
            # Replace all line items
            invoice.line_items.all().delete()
            for item_data in line_items:
                CommercialInvoiceLineItem.objects.create(
                    commercial_invoice=invoice,
                    **item_data,
                )

        invoice.save()
        return invoice


class PackingListService:
    """Service methods for Packing List management."""

    @staticmethod
    @transaction.atomic
    def create_packing_list(booking_id, user, line_items=None):
        """
        Create a Packing List for a booking.
        Auto-fills line items from the linked PI if no line_items provided.
        """
        try:
            booking = Booking.objects.get(pk=booking_id)
        except Booking.DoesNotExist:
            raise ValidationError({'booking_id': 'Booking not found.'})

        packing_list = PackingList.objects.create(
            booking=booking,
            created_by=user,
        )

        if line_items:
            for item_data in line_items:
                PackingListLineItem.objects.create(
                    packing_list=packing_list,
                    **item_data,
                )
        else:
            # Auto-fill from linked PI
            pi = booking.proforma_invoice
            if pi:
                for pi_item in pi.line_items.all():
                    PackingListLineItem.objects.create(
                        packing_list=packing_list,
                        product_name=pi_item.product_name,
                        quantity=pi_item.quantity,
                        num_packages=1,
                        net_weight=0,
                        gross_weight=0,
                        package_type='',
                    )

        return packing_list

    @staticmethod
    @transaction.atomic
    def finalize_packing_list(packing_list_id, user):
        """Finalize a Packing List (set status to FINALIZED)."""
        try:
            packing_list = PackingList.objects.get(pk=packing_list_id)
        except PackingList.DoesNotExist:
            raise ValidationError({'id': 'Packing List not found.'})

        if packing_list.status == PackingList.Status.FINALIZED:
            raise ValidationError(
                {'status': 'Packing List is already finalized.'}
            )

        packing_list.status = PackingList.Status.FINALIZED
        packing_list.save()
        return packing_list

    @staticmethod
    @transaction.atomic
    def create_revision(packing_list_id, user):
        """
        Create a new revision of a finalized Packing List.
        Creates a new DRAFT packing list with revision + 1, copying line items.
        """
        try:
            packing_list = PackingList.objects.get(pk=packing_list_id)
        except PackingList.DoesNotExist:
            raise ValidationError({'id': 'Packing List not found.'})

        if packing_list.status != PackingList.Status.FINALIZED:
            raise ValidationError(
                {'status': 'Only finalized packing lists can be revised.'}
            )

        new_packing_list = PackingList.objects.create(
            booking=packing_list.booking,
            revision=packing_list.revision + 1,
            created_by=user,
        )

        # Copy line items from the previous revision
        for item in packing_list.line_items.all():
            PackingListLineItem.objects.create(
                packing_list=new_packing_list,
                product_name=item.product_name,
                quantity=item.quantity,
                num_packages=item.num_packages,
                net_weight=item.net_weight,
                gross_weight=item.gross_weight,
                package_type=item.package_type,
            )

        return new_packing_list

    @staticmethod
    @transaction.atomic
    def update_packing_list(packing_list_id, user, line_items=None):
        """Update a Packing List's line items. Prevents edits to finalized docs."""
        try:
            packing_list = PackingList.objects.get(pk=packing_list_id)
        except PackingList.DoesNotExist:
            raise ValidationError({'id': 'Packing List not found.'})

        if packing_list.status == PackingList.Status.FINALIZED:
            raise ValidationError(
                {'status': 'Cannot edit a finalized packing list. Create a new revision instead.'}
            )

        if line_items is not None:
            packing_list.line_items.all().delete()
            for item_data in line_items:
                PackingListLineItem.objects.create(
                    packing_list=packing_list,
                    **item_data,
                )

        packing_list.save()
        return packing_list
