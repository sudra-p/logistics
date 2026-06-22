"""
Business logic service layer for Payment operations.
"""

from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from rest_framework import serializers

from payments.models import Payment
from proforma.models import ProformaInvoice
from proforma.services import ProformaService


class PaymentService:
    """Service class encapsulating Payment business logic."""

    @staticmethod
    @transaction.atomic
    def record_payment(data, user):
        """
        Validate amount, create payment, and auto-transition PI status.

        Rules:
        - On first payment against an APPROVED PI: transition PI to PAYMENT_PENDING
        - When total payments >= PI total_amount: transition PI to PAID

        Args:
            data: Dict of validated fields from PaymentCreateSerializer.
            user: The authenticated user creating the payment.

        Returns:
            The created Payment instance.
        """
        pi = data['proforma_invoice']

        # Re-validate amount under the transaction lock
        total_paid = (
            pi.payments.aggregate(total=Sum('amount'))['total']
            or Decimal('0.00')
        )
        remaining_balance = pi.total_amount - total_paid

        if data['amount'] > remaining_balance:
            raise serializers.ValidationError({
                'amount': (
                    f'Payment amount ({data["amount"]}) exceeds remaining balance '
                    f'({remaining_balance}) for {pi.pi_number}.'
                )
            })

        # Check if this is the first payment on an APPROVED PI
        is_first_payment = total_paid == Decimal('0.00')

        # Create the payment
        payment = Payment.objects.create(
            proforma_invoice=pi,
            amount=data['amount'],
            payment_mode=data['payment_mode'],
            payment_date=data['payment_date'],
            reference_number=data.get('reference_number', ''),
            notes=data.get('notes', ''),
            created_by=user,
        )

        # Auto-transition PI status
        new_total_paid = total_paid + data['amount']

        if is_first_payment and pi.status == ProformaInvoice.Status.APPROVED:
            # First payment on APPROVED PI: transition to PAYMENT_PENDING
            ProformaService.change_status(pi.pk, 'PAYMENT_PENDING', user)
            # Refresh PI status for next check
            pi.refresh_from_db()

        if new_total_paid >= pi.total_amount and pi.status == ProformaInvoice.Status.PAYMENT_PENDING:
            # Fully paid: transition to PAID
            ProformaService.change_status(pi.pk, 'PAID', user)

        return payment
