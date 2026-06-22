"""
DRF Serializers for Inventory/Stock management.
"""

from rest_framework import serializers

from inventory.models import StockItem, UNIT_CHOICES


class StockItemSerializer(serializers.ModelSerializer):
    """ModelSerializer for CRUD operations on StockItem."""

    class Meta:
        model = StockItem
        fields = [
            'id',
            'product_name',
            'available_stock',
            'reserved_stock',
            'shipped_stock',
            'unit',
            'updated_at',
        ]
        read_only_fields = ['id', 'updated_at']

    def validate_unit(self, value):
        valid_values = [choice[0] for choice in UNIT_CHOICES]
        if not value:
            return 'units'
        if value in valid_values:
            return value
        # Legacy bypass: allow if updating and value matches current DB value
        if self.instance and self.instance.unit == value:
            return value
        raise serializers.ValidationError(
            f"Invalid unit. Accepted values: {', '.join(valid_values)}"
        )


class ProductQuantityItemSerializer(serializers.Serializer):
    """Single item in a stuffing action: product + quantity."""

    product_name = serializers.CharField(max_length=255)
    quantity = serializers.IntegerField(min_value=1)


class StuffingActionSerializer(serializers.Serializer):
    """
    Validates the stuffing action payload.
    Expects a list of product_quantities: [{product_name, quantity}, ...]
    """

    product_quantities = ProductQuantityItemSerializer(many=True)

    def validate_product_quantities(self, value):
        if not value:
            raise serializers.ValidationError(
                'At least one product quantity is required.'
            )
        return value
