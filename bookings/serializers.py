"""
DRF Serializers for Booking creation and retrieval.
"""

from rest_framework import serializers

from bookings.models import Booking, BookingStatusHistory, Container, TranshipmentLeg
from bookings.validators import (
    validate_booking_dates,
    validate_certificates,
    validate_haz_fields,
    validate_master_data_references,
    validate_remarks,
)
from master_data.models import (
    Client,
    Commodity,
    Consignee,
    ContainerType,
    Forwarder,
    MarketingPerson,
    Port,
    Shipper,
    ShippingLine,
    Transporter,
    Vessel,
)
from proforma.models import ProformaInvoice


class BookingCreateSerializer(serializers.Serializer):
    """
    Serializer for booking creation.
    Validates all mandatory fields and runs cross-field validators.
    FK fields accept IDs (PrimaryKeyRelatedField).
    """

    # Dates (mandatory)
    booking_date = serializers.DateField(required=True)
    booking_validity_date = serializers.DateField(required=True)
    forwarding_window_start = serializers.DateField(required=True)
    forwarding_window_end = serializers.DateField(required=True)

    # Mandatory FK references
    shipping_line = serializers.PrimaryKeyRelatedField(
        queryset=ShippingLine.objects.all(), required=True
    )
    pol = serializers.PrimaryKeyRelatedField(
        queryset=Port.objects.all(), required=True
    )
    pod = serializers.PrimaryKeyRelatedField(
        queryset=Port.objects.all(), required=True
    )
    client = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(), required=True
    )
    commodity = serializers.PrimaryKeyRelatedField(
        queryset=Commodity.objects.all(), required=True
    )

    # Mandatory classification fields
    cargo_type = serializers.ChoiceField(
        choices=Booking.CargoType.choices, required=True
    )
    shipment_type = serializers.CharField(max_length=50, required=True)
    stuffing_type = serializers.CharField(max_length=50, required=True)

    # Optional Proforma Invoice link
    proforma_invoice = serializers.PrimaryKeyRelatedField(
        queryset=ProformaInvoice.objects.all(), required=False, allow_null=True
    )

    # Optional FK references
    vessel = serializers.PrimaryKeyRelatedField(
        queryset=Vessel.objects.all(), required=False, allow_null=True
    )
    por = serializers.PrimaryKeyRelatedField(
        queryset=Port.objects.all(), required=False, allow_null=True
    )
    fpd = serializers.PrimaryKeyRelatedField(
        queryset=Port.objects.all(), required=False, allow_null=True
    )
    transporter = serializers.PrimaryKeyRelatedField(
        queryset=Transporter.objects.all(), required=False, allow_null=True
    )
    marketing_person = serializers.PrimaryKeyRelatedField(
        queryset=MarketingPerson.objects.all(), required=False, allow_null=True
    )
    nvocc_forwarder = serializers.PrimaryKeyRelatedField(
        queryset=Forwarder.objects.all(), required=False, allow_null=True
    )
    shipper = serializers.PrimaryKeyRelatedField(
        queryset=Shipper.objects.all(), required=False, allow_null=True
    )
    consignee = serializers.PrimaryKeyRelatedField(
        queryset=Consignee.objects.all(), required=False, allow_null=True
    )

    # Optional scalar fields
    booking_no = serializers.CharField(max_length=50, required=False, allow_blank=True)
    voyage = serializers.CharField(max_length=100, required=False, allow_blank=True)
    etd_pol = serializers.DateTimeField(required=False, allow_null=True)
    eta_destination = serializers.DateTimeField(required=False, allow_null=True)
    si_cut_off = serializers.DateTimeField(required=False, allow_null=True)
    vgm_cut_off = serializers.DateTimeField(required=False, allow_null=True)
    sb_cut_off = serializers.DateTimeField(required=False, allow_null=True)
    gate_cut_off = serializers.DateTimeField(required=False, allow_null=True)
    clearance_point = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    stuffing_point = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    expected_stuffing_date = serializers.DateField(required=False, allow_null=True)
    is_icd_hand_over = serializers.BooleanField(required=False, default=False)
    transport_involved = serializers.BooleanField(required=False, default=False)
    clearance_involved = serializers.BooleanField(required=False, default=False)
    buyer = serializers.CharField(max_length=255, required=False, allow_blank=True)
    quotation_no = serializers.CharField(
        max_length=50, required=False, allow_blank=True
    )
    docs_holder = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    po_no = serializers.CharField(max_length=100, required=False, allow_blank=True)
    shipper_invoice_no = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )
    hbl_no = serializers.CharField(max_length=50, required=False, allow_blank=True)
    mbl_no = serializers.CharField(max_length=50, required=False, allow_blank=True)
    hbl_freight_terms = serializers.ChoiceField(
        choices=Booking.FreightTerms.choices, required=False, allow_blank=True
    )
    mbl_freight_terms = serializers.ChoiceField(
        choices=Booking.FreightTerms.choices, required=False, allow_blank=True
    )
    bl_type = serializers.CharField(max_length=50, required=False, allow_blank=True)
    mbl_type = serializers.CharField(max_length=50, required=False, allow_blank=True)

    # Certificates (JSON list, max 5)
    certificates = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        max_length=5,
    )

    # HAZ fields
    is_haz = serializers.BooleanField(required=False, default=False)
    haz_class = serializers.CharField(max_length=50, required=False, allow_blank=True)
    haz_uin = serializers.CharField(max_length=100, required=False, allow_blank=True)
    haz_group = serializers.CharField(max_length=50, required=False, allow_blank=True)

    # Remarks
    remarks = serializers.CharField(
        max_length=2000, required=False, allow_blank=True
    )

    def validate(self, data):
        """Run all cross-field validators."""
        # Date ordering validation
        validate_booking_dates(data)

        # HAZ conditional fields validation
        data = validate_haz_fields(data)

        # Certificates validation
        certificates = data.get('certificates')
        if certificates is not None:
            validate_certificates(certificates)

        # Remarks validation
        remarks = data.get('remarks')
        if remarks:
            validate_remarks(remarks)

        # Master data FK reference validation
        validate_master_data_references(data)

        return data


class BookingUpdateSerializer(serializers.Serializer):
    """
    Serializer for booking updates (partial update supported).
    All fields are optional. Cross-field validators run on merged data
    (existing booking values + new fields).
    """

    # Dates
    booking_date = serializers.DateField(required=False)
    booking_validity_date = serializers.DateField(required=False)
    forwarding_window_start = serializers.DateField(required=False)
    forwarding_window_end = serializers.DateField(required=False)

    # Mandatory FK references (optional in update context)
    shipping_line = serializers.PrimaryKeyRelatedField(
        queryset=ShippingLine.objects.all(), required=False
    )
    pol = serializers.PrimaryKeyRelatedField(
        queryset=Port.objects.all(), required=False
    )
    pod = serializers.PrimaryKeyRelatedField(
        queryset=Port.objects.all(), required=False
    )
    client = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(), required=False
    )
    commodity = serializers.PrimaryKeyRelatedField(
        queryset=Commodity.objects.all(), required=False
    )

    # Classification fields
    cargo_type = serializers.ChoiceField(
        choices=Booking.CargoType.choices, required=False
    )
    shipment_type = serializers.CharField(max_length=50, required=False)
    stuffing_type = serializers.CharField(max_length=50, required=False)

    # Optional Proforma Invoice link
    proforma_invoice = serializers.PrimaryKeyRelatedField(
        queryset=ProformaInvoice.objects.all(), required=False, allow_null=True
    )

    # Optional FK references
    vessel = serializers.PrimaryKeyRelatedField(
        queryset=Vessel.objects.all(), required=False, allow_null=True
    )
    por = serializers.PrimaryKeyRelatedField(
        queryset=Port.objects.all(), required=False, allow_null=True
    )
    fpd = serializers.PrimaryKeyRelatedField(
        queryset=Port.objects.all(), required=False, allow_null=True
    )
    transporter = serializers.PrimaryKeyRelatedField(
        queryset=Transporter.objects.all(), required=False, allow_null=True
    )
    marketing_person = serializers.PrimaryKeyRelatedField(
        queryset=MarketingPerson.objects.all(), required=False, allow_null=True
    )
    nvocc_forwarder = serializers.PrimaryKeyRelatedField(
        queryset=Forwarder.objects.all(), required=False, allow_null=True
    )
    shipper = serializers.PrimaryKeyRelatedField(
        queryset=Shipper.objects.all(), required=False, allow_null=True
    )
    consignee = serializers.PrimaryKeyRelatedField(
        queryset=Consignee.objects.all(), required=False, allow_null=True
    )

    # Optional scalar fields
    booking_no = serializers.CharField(max_length=50, required=False, allow_blank=True)
    voyage = serializers.CharField(max_length=100, required=False, allow_blank=True)
    etd_pol = serializers.DateTimeField(required=False, allow_null=True)
    eta_destination = serializers.DateTimeField(required=False, allow_null=True)
    si_cut_off = serializers.DateTimeField(required=False, allow_null=True)
    vgm_cut_off = serializers.DateTimeField(required=False, allow_null=True)
    sb_cut_off = serializers.DateTimeField(required=False, allow_null=True)
    gate_cut_off = serializers.DateTimeField(required=False, allow_null=True)
    clearance_point = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    stuffing_point = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    expected_stuffing_date = serializers.DateField(required=False, allow_null=True)
    is_icd_hand_over = serializers.BooleanField(required=False)
    transport_involved = serializers.BooleanField(required=False)
    clearance_involved = serializers.BooleanField(required=False)
    buyer = serializers.CharField(max_length=255, required=False, allow_blank=True)
    quotation_no = serializers.CharField(
        max_length=50, required=False, allow_blank=True
    )
    docs_holder = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    po_no = serializers.CharField(max_length=100, required=False, allow_blank=True)
    shipper_invoice_no = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )
    hbl_no = serializers.CharField(max_length=50, required=False, allow_blank=True)
    mbl_no = serializers.CharField(max_length=50, required=False, allow_blank=True)
    hbl_freight_terms = serializers.ChoiceField(
        choices=Booking.FreightTerms.choices, required=False, allow_blank=True
    )
    mbl_freight_terms = serializers.ChoiceField(
        choices=Booking.FreightTerms.choices, required=False, allow_blank=True
    )
    bl_type = serializers.CharField(max_length=50, required=False, allow_blank=True)
    mbl_type = serializers.CharField(max_length=50, required=False, allow_blank=True)

    # Certificates (JSON list, max 5)
    certificates = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        max_length=5,
    )

    # HAZ fields
    is_haz = serializers.BooleanField(required=False)
    haz_class = serializers.CharField(max_length=50, required=False, allow_blank=True)
    haz_uin = serializers.CharField(max_length=100, required=False, allow_blank=True)
    haz_group = serializers.CharField(max_length=50, required=False, allow_blank=True)

    # Remarks
    remarks = serializers.CharField(
        max_length=2000, required=False, allow_blank=True
    )

    def __init__(self, *args, **kwargs):
        self.booking_instance = kwargs.pop('booking_instance', None)
        super().__init__(*args, **kwargs)

    def _get_merged_data(self, data):
        """
        Merge the submitted update data with existing booking values
        so cross-field validators can check the full picture.
        """
        if not self.booking_instance:
            return data

        # Build merged dict from existing booking for date/FK fields needed by validators
        merged = {}

        # Date fields
        date_fields = [
            'booking_date', 'booking_validity_date',
            'forwarding_window_start', 'forwarding_window_end',
        ]
        for field in date_fields:
            if field in data:
                merged[field] = data[field]
            else:
                merged[field] = getattr(self.booking_instance, field)

        # FK fields (resolve to instance for validator compatibility)
        fk_fields = [
            'shipping_line', 'pol', 'pod', 'client', 'commodity',
            'vessel', 'transporter', 'por', 'fpd', 'marketing_person',
            'nvocc_forwarder', 'shipper', 'consignee',
        ]
        for field in fk_fields:
            if field in data:
                merged[field] = data[field]
            else:
                merged[field] = getattr(self.booking_instance, field)

        # HAZ fields
        haz_fields = ['is_haz', 'haz_class', 'haz_uin', 'haz_group']
        for field in haz_fields:
            if field in data:
                merged[field] = data[field]
            else:
                merged[field] = getattr(self.booking_instance, field)

        # Certificates
        if 'certificates' in data:
            merged['certificates'] = data['certificates']
        else:
            merged['certificates'] = self.booking_instance.certificates

        # Remarks
        if 'remarks' in data:
            merged['remarks'] = data['remarks']
        else:
            merged['remarks'] = self.booking_instance.remarks

        return merged

    def validate(self, data):
        """Run cross-field validators on merged data (existing + new)."""
        merged = self._get_merged_data(data)

        # Date ordering validation
        validate_booking_dates(merged)

        # HAZ conditional fields validation
        merged = validate_haz_fields(merged)

        # Update data with HAZ results (in case is_haz=False cleared fields)
        for haz_field in ['haz_class', 'haz_uin', 'haz_group']:
            if haz_field in merged:
                data[haz_field] = merged[haz_field]

        # If is_haz was in merged but not in data (came from existing booking),
        # and HAZ fields were cleared, include them in data
        if 'is_haz' not in data and not merged.get('is_haz', False):
            data['haz_class'] = ''
            data['haz_uin'] = ''
            data['haz_group'] = ''

        # Certificates validation
        certificates = merged.get('certificates')
        if certificates is not None:
            validate_certificates(certificates)

        # Remarks validation
        remarks = merged.get('remarks')
        if remarks:
            validate_remarks(remarks)

        # Master data FK reference validation
        validate_master_data_references(merged)

        return data


class BookingDetailSerializer(serializers.ModelSerializer):
    """Serializer for booking retrieval (read-only detail view)."""

    proforma_invoice = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ['job_number', 'status', 'created_by', 'created_at', 'updated_at']


class ContainerSerializer(serializers.Serializer):
    """Serializer for creating individual container entries."""

    ALLOWED_SIZES = ['20FT', '40FT', '40FT_HC', '45FT']

    container_type = serializers.PrimaryKeyRelatedField(
        queryset=ContainerType.objects.all(), required=True
    )
    container_size = serializers.ChoiceField(
        choices=Container.Size.choices, required=True
    )
    container_count = serializers.IntegerField(min_value=1, required=True)
    container_no = serializers.CharField(
        max_length=20, required=False, allow_blank=True, default=''
    )
    seal_no = serializers.CharField(
        max_length=20, required=False, allow_blank=True, default=''
    )

    def validate_container_size(self, value):
        if value not in self.ALLOWED_SIZES:
            raise serializers.ValidationError(
                f'Invalid container size. Must be one of: {", ".join(self.ALLOWED_SIZES)}'
            )
        return value


class ContainerDetailSerializer(serializers.ModelSerializer):
    """Read-only serializer for container retrieval."""

    class Meta:
        model = Container
        fields = [
            'id', 'container_type', 'container_size', 'container_count',
            'container_no', 'seal_no', 'stuffing_status', 'stuffed_at',
        ]
        read_only_fields = ['id', 'stuffing_status', 'stuffed_at']


class TranshipmentLegSerializer(serializers.Serializer):
    """Serializer for creating/updating individual transhipment legs."""

    port = serializers.PrimaryKeyRelatedField(
        queryset=Port.objects.all(), required=True
    )
    eta = serializers.DateTimeField(required=True)
    connecting_vessel_voyage = serializers.CharField(
        max_length=200, required=True
    )
    etd = serializers.DateTimeField(required=True)


class TranshipmentLegDetailSerializer(serializers.ModelSerializer):
    """Read-only serializer for transhipment leg retrieval."""

    class Meta:
        model = TranshipmentLeg
        fields = ['id', 'sequence', 'port', 'eta', 'connecting_vessel_voyage', 'etd']
        read_only_fields = ['id', 'sequence']


class TranshipmentLegsCreateSerializer(serializers.Serializer):
    """Serializer for adding multiple transhipment legs at once."""

    legs = TranshipmentLegSerializer(many=True)

    def validate_legs(self, value):
        if not value:
            raise serializers.ValidationError('At least one transhipment leg is required.')
        return value


class StatusChangeSerializer(serializers.Serializer):
    """Serializer for booking status change requests."""

    status = serializers.ChoiceField(choices=Booking.Status.choices, required=True)


class BookingStatusHistorySerializer(serializers.ModelSerializer):
    """Read-only serializer for booking status history records."""

    class Meta:
        model = BookingStatusHistory
        fields = [
            'id',
            'previous_status',
            'new_status',
            'changed_by',
            'changed_at',
        ]
        read_only_fields = fields
