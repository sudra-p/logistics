from rest_framework import serializers

from bookings.models import Booking


class PendingDOReportSerializer(serializers.ModelSerializer):
    """Serializer for the Pending DO Report."""

    booking_reference = serializers.CharField(source='job_number')
    client_name = serializers.CharField(source='client.name')
    vessel_voyage = serializers.SerializerMethodField()
    pol = serializers.CharField(source='pol.name')
    pod = serializers.CharField(source='pod.name')
    shipping_line = serializers.CharField(source='shipping_line.name')
    container_count = serializers.IntegerField(
        source='total_container_count', default=0
    )
    status_display = serializers.CharField(source='get_status_display')

    class Meta:
        model = Booking
        fields = [
            'booking_reference',
            'client_name',
            'vessel_voyage',
            'pol',
            'pod',
            'etd_pol',
            'eta_destination',
            'status_display',
            'shipping_line',
            'container_count',
            'booking_date',
        ]

    def get_vessel_voyage(self, obj):
        """Combine vessel name and voyage into a single field."""
        parts = []
        if obj.vessel:
            parts.append(obj.vessel.name)
        if obj.voyage:
            parts.append(obj.voyage)
        return ' / '.join(parts) if parts else ''


class MasterReportSerializer(serializers.ModelSerializer):
    """Serializer for the Master Report."""

    booking_reference = serializers.CharField(source='job_number')
    client_name = serializers.CharField(source='client.name')
    vessel_voyage = serializers.SerializerMethodField()
    pol = serializers.CharField(source='pol.name')
    pod = serializers.CharField(source='pod.name')
    shipping_line = serializers.CharField(source='shipping_line.name')
    container_count = serializers.IntegerField(
        source='total_container_count', default=0
    )
    status_display = serializers.CharField(source='get_status_display')
    created_date = serializers.DateTimeField(source='created_at')

    class Meta:
        model = Booking
        fields = [
            'booking_reference',
            'client_name',
            'vessel_voyage',
            'pol',
            'pod',
            'etd_pol',
            'eta_destination',
            'status_display',
            'shipping_line',
            'container_count',
            'created_date',
        ]

    def get_vessel_voyage(self, obj):
        """Combine vessel name and voyage into a single field."""
        parts = []
        if obj.vessel:
            parts.append(obj.vessel.name)
        if obj.voyage:
            parts.append(obj.voyage)
        return ' / '.join(parts) if parts else ''
