"""
DRF Serializers for Payment operations.
"""

from decimal import Decimal

from django.db.models import Sum
from rest_framework import serializers

from payments.models import Payment
from proforma.models import ProformaInvoice


class PaymentCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a Payment.
    Validates that payment amount does not exceed the remaining balance on the PI.
    """

    proforma_invoice = serializers.PrimaryKeyRelatedField(
        queryset=ProformaInvoice.objects.all(), required=True
    )
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, required=True)
    payment_mode = serializers.ChoiceField(
        choices=Payment.PaymentMode.choices, required=True
    )
    payment_date = serializers.DateField(required=True)
    reference_number = serializers.CharField(max_length=100, required=False, default='')
    notes = serializers.CharField(required=False, default='')

    def validate_amount(self, value):
        """Amount must be positive."""
        if value <= Decimal('0'):
            raise serializers.ValidationError('Payment amount must be greater than zero.')
        return value

    def validate(self, data):
        """Validate that amount does not exceed remaining balance."""
        pi = data['proforma_invoice']
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

        return data


class PaymentDetailSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for Payment detail view.
    Includes customer_name, pi_number, pi_total_amount, outstanding_balance.
    """

    customer_name = serializers.CharField(
        source='proforma_invoice.customer.name', read_only=True
    )
    pi_number = serializers.CharField(
        source='proforma_invoice.pi_number', read_only=True
    )
    pi_total_amount = serializers.DecimalField(
        source='proforma_invoice.total_amount',
        max_digits=15,
        decimal_places=2,
        read_only=True,
    )
    outstanding_balance = serializers.SerializerMethodField()
    created_by_username = serializers.CharField(
        source='created_by.username', read_only=True
    )

    class Meta:
        model = Payment
        fields = [
            'id',
            'proforma_invoice',
            'pi_number',
            'customer_name',
            'pi_total_amount',
            'outstanding_balance',
            'amount',
            'payment_mode',
            'payment_date',
            'reference_number',
            'notes',
            'created_by',
            'created_by_username',
            'created_at',
        ]
        read_only_fields = fields

    def get_outstanding_balance(self, obj):
        """Compute outstanding balance: PI total - sum of all payments for the PI."""
        total_paid = (
            obj.proforma_invoice.payments.aggregate(total=Sum('amount'))['total']
            or Decimal('0.00')
        )
        return str(obj.proforma_invoice.total_amount - total_paid)
