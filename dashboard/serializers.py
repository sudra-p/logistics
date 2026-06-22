"""
Serializers for the Dashboard app.
"""

from rest_framework import serializers

from bookings.models import Booking, Container
from proforma.models import ProformaInvoice


class ProformaStatusSerializer(serializers.ModelSerializer):
    """
    Serializer for the Proforma Status dashboard section.
    Returns pi_number, customer_name, amount, and status for non-Paid PIs.
    """

    customer_name = serializers.CharField(source='customer.name', read_only=True)
    amount = serializers.DecimalField(
        source='total_amount', max_digits=15, decimal_places=2, read_only=True
    )

    class Meta:
        model = ProformaInvoice
        fields = ['pi_number', 'customer_name', 'amount', 'status']
        read_only_fields = fields


class ContainerBriefSerializer(serializers.ModelSerializer):
    """Brief container info for the current shipments dashboard."""

    class Meta:
        model = Container
        fields = ['container_no', 'container_size', 'container_count']
        read_only_fields = fields


class CurrentShipmentsSerializer(serializers.ModelSerializer):
    """
    Serializer for the Current Shipments dashboard section.
    Returns job_number, customer name, container info, status, ETD, and ETA
    for all active Bookings (status != COMPLETED).
    """

    customer = serializers.CharField(source='client.name', read_only=True)
    containers = ContainerBriefSerializer(many=True, read_only=True)
    etd = serializers.DateTimeField(source='etd_pol', read_only=True)
    eta = serializers.DateTimeField(source='eta_destination', read_only=True)

    class Meta:
        model = Booking
        fields = ['job_number', 'customer', 'containers', 'status', 'etd', 'eta']
        read_only_fields = fields
