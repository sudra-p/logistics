"""
DRF Serializers for Proforma Invoice CRUD operations.
"""

from decimal import Decimal

from rest_framework import serializers

from master_data.models import Client
from proforma.models import ProformaInvoice, ProformaLineItem


class ProformaLineItemSerializer(serializers.ModelSerializer):
    """Serializer for ProformaLineItem (nested writable)."""

    class Meta:
        model = ProformaLineItem
        fields = ['id', 'product_name', 'quantity', 'rate', 'amount']
        read_only_fields = ['id']

    def validate(self, data):
        """Auto-compute amount = quantity * rate if not provided, or validate it matches."""
        quantity = data.get('quantity')
        rate = data.get('rate')
        amount = data.get('amount')

        if quantity is not None and rate is not None:
            computed_amount = Decimal(str(quantity)) * Decimal(str(rate))
            if amount is None:
                data['amount'] = computed_amount
            else:
                # Validate that provided amount matches quantity * rate
                if Decimal(str(amount)) != computed_amount:
                    raise serializers.ValidationError({
                        'amount': (
                            f'Amount ({amount}) does not match '
                            f'quantity ({quantity}) × rate ({rate}) = {computed_amount}.'
                        )
                    })
        return data


class ProformaInvoiceCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a Proforma Invoice with nested line items.
    Validates customer FK, currency, dates, and line_items.
    """

    date = serializers.DateField(required=True)
    customer = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(), required=True
    )
    currency = serializers.ChoiceField(
        choices=ProformaInvoice.Currency.choices, required=True
    )
    exchange_rate = serializers.DecimalField(
        max_digits=10, decimal_places=4, required=False, default=Decimal('1.0000')
    )
    payment_terms = serializers.CharField(required=True)
    expected_shipment_date = serializers.DateField(required=True)
    line_items = ProformaLineItemSerializer(many=True)

    def validate_line_items(self, value):
        """At least one line item must exist."""
        if not value:
            raise serializers.ValidationError(
                'At least one line item is required.'
            )
        return value

    def validate(self, data):
        """Cross-field validation."""
        # Ensure expected_shipment_date is on or after date
        if data.get('date') and data.get('expected_shipment_date'):
            if data['expected_shipment_date'] < data['date']:
                raise serializers.ValidationError({
                    'expected_shipment_date': (
                        'Expected shipment date cannot be before the invoice date.'
                    )
                })
        return data


class ProformaInvoiceUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating a Proforma Invoice.
    Replaces all line items on update.
    """

    date = serializers.DateField(required=False)
    customer = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(), required=False
    )
    currency = serializers.ChoiceField(
        choices=ProformaInvoice.Currency.choices, required=False
    )
    exchange_rate = serializers.DecimalField(
        max_digits=10, decimal_places=4, required=False
    )
    payment_terms = serializers.CharField(required=False)
    expected_shipment_date = serializers.DateField(required=False)
    line_items = ProformaLineItemSerializer(many=True, required=False)

    def validate_line_items(self, value):
        """If line_items are provided, at least one must exist."""
        if value is not None and len(value) == 0:
            raise serializers.ValidationError(
                'At least one line item is required.'
            )
        return value


class ProformaInvoiceDetailSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for Proforma Invoice detail view.
    Includes nested line_items, customer name, and payment_summary.
    """

    line_items = ProformaLineItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    payment_summary = serializers.SerializerMethodField()

    class Meta:
        model = ProformaInvoice
        fields = [
            'id',
            'pi_number',
            'date',
            'customer',
            'customer_name',
            'currency',
            'exchange_rate',
            'payment_terms',
            'expected_shipment_date',
            'total_amount',
            'status',
            'created_by',
            'created_at',
            'updated_at',
            'line_items',
            'payment_summary',
        ]
        read_only_fields = fields

    def get_payment_summary(self, obj):
        """Compute payment summary: total_paid, outstanding_balance, payment_status."""
        from django.db.models import Sum

        # Handle case where payments app may not be installed yet
        try:
            total_paid = (
                obj.payments.aggregate(total=Sum('amount'))['total']
                or Decimal('0.00')
            )
        except Exception:
            total_paid = Decimal('0.00')

        outstanding_balance = obj.total_amount - total_paid

        if total_paid >= obj.total_amount and obj.total_amount > 0:
            payment_status = 'Fully_Paid'
        elif total_paid > 0:
            payment_status = 'Partial_Paid'
        else:
            payment_status = 'Unpaid'

        return {
            'total_paid': str(total_paid),
            'outstanding_balance': str(outstanding_balance),
            'payment_status': payment_status,
        }
