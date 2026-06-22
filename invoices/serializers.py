"""
DRF Serializers for Commercial Invoice and Packing List.
"""

from rest_framework import serializers

from .models import (
    CommercialInvoice,
    CommercialInvoiceLineItem,
    PackingList,
    PackingListLineItem,
)


# --- Commercial Invoice Serializers ---


class CommercialInvoiceLineItemSerializer(serializers.ModelSerializer):
    """Serializer for CommercialInvoiceLineItem (nested writable)."""

    class Meta:
        model = CommercialInvoiceLineItem
        fields = [
            'id', 'product_name', 'quantity', 'rate', 'amount',
            'net_weight', 'gross_weight', 'hs_code', 'num_packages',
        ]
        read_only_fields = ['id']


class CommercialInvoiceCreateSerializer(serializers.Serializer):
    """Serializer for creating a Commercial Invoice (auto-fill from PI)."""

    booking_id = serializers.IntegerField(required=True)
    line_items = CommercialInvoiceLineItemSerializer(many=True, required=False)


class CommercialInvoiceUpdateSerializer(serializers.Serializer):
    """Serializer for updating a Commercial Invoice."""

    line_items = CommercialInvoiceLineItemSerializer(many=True, required=False)


class CommercialInvoiceDetailSerializer(serializers.ModelSerializer):
    """Read-only serializer for Commercial Invoice detail."""

    line_items = CommercialInvoiceLineItemSerializer(many=True, read_only=True)
    booking_job_number = serializers.CharField(
        source='booking.job_number', read_only=True
    )

    class Meta:
        model = CommercialInvoice
        fields = [
            'id', 'invoice_number', 'booking', 'booking_job_number',
            'revision', 'status', 'created_by', 'created_at', 'updated_at',
            'line_items',
        ]
        read_only_fields = fields


# --- Packing List Serializers ---


class PackingListLineItemSerializer(serializers.ModelSerializer):
    """Serializer for PackingListLineItem (nested writable)."""

    class Meta:
        model = PackingListLineItem
        fields = [
            'id', 'product_name', 'quantity', 'num_packages',
            'net_weight', 'gross_weight', 'package_type',
        ]
        read_only_fields = ['id']


class PackingListCreateSerializer(serializers.Serializer):
    """Serializer for creating a Packing List."""

    booking_id = serializers.IntegerField(required=True)
    line_items = PackingListLineItemSerializer(many=True, required=False)


class PackingListUpdateSerializer(serializers.Serializer):
    """Serializer for updating a Packing List."""

    line_items = PackingListLineItemSerializer(many=True, required=False)


class PackingListDetailSerializer(serializers.ModelSerializer):
    """Read-only serializer for Packing List detail."""

    line_items = PackingListLineItemSerializer(many=True, read_only=True)
    booking_job_number = serializers.CharField(
        source='booking.job_number', read_only=True
    )

    class Meta:
        model = PackingList
        fields = [
            'id', 'packing_list_number', 'booking', 'booking_job_number',
            'revision', 'status', 'created_by', 'created_at', 'updated_at',
            'line_items',
        ]
        read_only_fields = fields
