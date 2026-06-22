"""
DRF Serializers for Bill of Lading.
"""

from rest_framework import serializers

from master_data.models import Consignee, Shipper

from .models import BillOfLading


class BillOfLadingCreateSerializer(serializers.Serializer):
    """Serializer for creating a Bill of Lading."""

    booking_id = serializers.IntegerField(required=True)
    bl_number = serializers.CharField(max_length=50, required=True)
    bl_type = serializers.ChoiceField(choices=BillOfLading.BLType.choices, required=True)
    container_number = serializers.CharField(max_length=50, required=False, default='')
    vessel_name = serializers.CharField(max_length=255, required=False, default='')
    voyage_number = serializers.CharField(max_length=100, required=False, default='')
    shipper = serializers.PrimaryKeyRelatedField(
        queryset=Shipper.objects.all(), required=False, allow_null=True
    )
    consignee = serializers.PrimaryKeyRelatedField(
        queryset=Consignee.objects.all(), required=False, allow_null=True
    )
    notify_party = serializers.CharField(required=False, allow_blank=True, default='')
    cargo_description = serializers.CharField(required=False, allow_blank=True, default='')


class BillOfLadingUpdateSerializer(serializers.Serializer):
    """Serializer for updating a Bill of Lading."""

    bl_type = serializers.ChoiceField(choices=BillOfLading.BLType.choices, required=False)
    container_number = serializers.CharField(max_length=50, required=False)
    vessel_name = serializers.CharField(max_length=255, required=False)
    voyage_number = serializers.CharField(max_length=100, required=False)
    shipper = serializers.PrimaryKeyRelatedField(
        queryset=Shipper.objects.all(), required=False
    )
    consignee = serializers.PrimaryKeyRelatedField(
        queryset=Consignee.objects.all(), required=False
    )
    notify_party = serializers.CharField(required=False, allow_blank=True)
    cargo_description = serializers.CharField(required=False, allow_blank=True)


class BillOfLadingDetailSerializer(serializers.ModelSerializer):
    """Read-only serializer for Bill of Lading detail."""

    booking_job_number = serializers.CharField(
        source='booking.job_number', read_only=True
    )
    shipper_name = serializers.CharField(
        source='shipper.name', read_only=True
    )
    consignee_name = serializers.CharField(
        source='consignee.name', read_only=True
    )

    class Meta:
        model = BillOfLading
        fields = [
            'id', 'bl_number', 'booking', 'booking_job_number',
            'bl_type', 'status', 'container_number',
            'vessel_name', 'voyage_number',
            'shipper', 'shipper_name',
            'consignee', 'consignee_name',
            'notify_party', 'cargo_description',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = fields


class BillOfLadingStatusSerializer(serializers.Serializer):
    """Serializer for BL status change."""

    status = serializers.ChoiceField(choices=BillOfLading.Status.choices, required=True)
