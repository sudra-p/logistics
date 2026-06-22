"""
Serializers for the Operations Tracking View.
"""

from rest_framework import serializers

from bookings.models import Booking


class OperationsTrackingSerializer(serializers.ModelSerializer):
    """
    Serializer for the Operations tracking view.
    Displays consolidated shipment tracking data from Bookings and related models.

    Returns fields: pi_number, booking_number (job_number), consignee,
    shipping_line, container_type, vessel_name, voyage, pol, pod, fpd,
    etd, eta, forwarder.
    """

    pi_number = serializers.SerializerMethodField()
    booking_number = serializers.CharField(source='job_number', read_only=True)
    consignee = serializers.SerializerMethodField()
    shipping_line = serializers.SerializerMethodField()
    container_type = serializers.SerializerMethodField()
    vessel_name = serializers.SerializerMethodField()
    voyage = serializers.CharField(read_only=True)
    pol = serializers.SerializerMethodField()
    pod = serializers.SerializerMethodField()
    fpd = serializers.SerializerMethodField()
    etd = serializers.DateTimeField(source='etd_pol', read_only=True)
    eta = serializers.DateTimeField(source='eta_destination', read_only=True)
    forwarder = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id',
            'pi_number',
            'booking_number',
            'consignee',
            'shipping_line',
            'container_type',
            'vessel_name',
            'voyage',
            'pol',
            'pod',
            'fpd',
            'etd',
            'eta',
            'forwarder',
        ]

    def get_pi_number(self, obj):
        """Return PI number from linked proforma invoice."""
        if obj.proforma_invoice:
            return obj.proforma_invoice.pi_number
        return None

    def get_consignee(self, obj):
        """Return consignee name."""
        if obj.consignee:
            return obj.consignee.name
        return None

    def get_shipping_line(self, obj):
        """Return shipping line name."""
        if obj.shipping_line:
            return obj.shipping_line.name
        return None

    def get_container_type(self, obj):
        """Return container type from the first container on the booking."""
        containers = obj.containers.all()
        if containers:
            first_container = containers[0]
            if first_container.container_type:
                return first_container.container_type.name
        return None

    def get_vessel_name(self, obj):
        """Return vessel name."""
        if obj.vessel:
            return obj.vessel.name
        return None

    def get_pol(self, obj):
        """Return port of loading name."""
        if obj.pol:
            return obj.pol.name
        return None

    def get_pod(self, obj):
        """Return port of discharge name."""
        if obj.pod:
            return obj.pod.name
        return None

    def get_fpd(self, obj):
        """Return final place of delivery name."""
        if obj.fpd:
            return obj.fpd.name
        return None

    def get_forwarder(self, obj):
        """Return NVOCC forwarder name."""
        if obj.nvocc_forwarder:
            return obj.nvocc_forwarder.name
        return None
