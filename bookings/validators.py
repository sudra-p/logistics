"""
Cross-field validators for booking creation and updates.

All validation functions raise rest_framework.serializers.ValidationError
with field-level error messages in the format: {"field_name": ["Error description."]}.
"""

from rest_framework import serializers

from master_data.models import (
    Client,
    Commodity,
    Consignee,
    Forwarder,
    MarketingPerson,
    Port,
    Shipper,
    ShippingLine,
    Transporter,
    Vessel,
)

MAX_TRANSHIPMENT_LEGS = 4


def validate_booking_dates(data):
    """
    Validate date ordering constraints:
    - booking_validity_date >= booking_date
    - forwarding_window_end >= forwarding_window_start
    """
    errors = {}

    booking_date = data.get('booking_date')
    booking_validity_date = data.get('booking_validity_date')
    forwarding_window_start = data.get('forwarding_window_start')
    forwarding_window_end = data.get('forwarding_window_end')

    if booking_date and booking_validity_date:
        if booking_validity_date < booking_date:
            errors['booking_validity_date'] = [
                'Booking Validity Date must be on or after Booking Date.'
            ]

    if forwarding_window_start and forwarding_window_end:
        if forwarding_window_end < forwarding_window_start:
            errors['forwarding_window_end'] = [
                'Forwarding Window End Date must be on or after Forwarding Window Start Date.'
            ]

    if errors:
        raise serializers.ValidationError(errors)

    return data


def validate_haz_fields(data):
    """
    Validate HAZ conditional fields:
    - If is_haz=True: haz_class, haz_uin, haz_group must be non-empty.
    - If is_haz=False: clear/discard haz_class, haz_uin, haz_group values.

    Returns the (possibly modified) data dict.
    """
    is_haz = data.get('is_haz', False)

    if is_haz:
        errors = {}
        if not data.get('haz_class'):
            errors['haz_class'] = ['HAZ Class is required when Is HAZ is true.']
        if not data.get('haz_uin'):
            errors['haz_uin'] = ['HAZ UIN is required when Is HAZ is true.']
        if not data.get('haz_group'):
            errors['haz_group'] = ['HAZ Group is required when Is HAZ is true.']
        if errors:
            raise serializers.ValidationError(errors)
    else:
        # Discard HAZ fields when is_haz is False
        data['haz_class'] = ''
        data['haz_uin'] = ''
        data['haz_group'] = ''

    return data


def validate_certificates(certificates):
    """
    Validate the certificates field:
    - Must be a list.
    - Max 5 entries.
    - Each entry must be a string.
    """
    if certificates is None:
        return certificates

    errors = {}

    if not isinstance(certificates, list):
        errors['certificates'] = ['Certificates must be a list.']
        raise serializers.ValidationError(errors)

    if len(certificates) > 5:
        errors['certificates'] = ['A maximum of 5 certificates are allowed.']
        raise serializers.ValidationError(errors)

    for i, entry in enumerate(certificates):
        if not isinstance(entry, str):
            errors['certificates'] = [
                f'Each certificate entry must be a string. Entry at index {i} is invalid.'
            ]
            raise serializers.ValidationError(errors)

    return certificates


def validate_remarks(remarks):
    """
    Validate the remarks field:
    - Max 2000 characters.
    """
    if remarks and len(remarks) > 2000:
        raise serializers.ValidationError(
            {'remarks': ['Remarks must not exceed 2000 characters.']}
        )
    return remarks


def validate_master_data_references(data):
    """
    Validate that all FK IDs reference existing master data records.

    Mandatory references (must exist):
    - client, shipping_line, pol, pod, commodity

    Optional references (validated only if provided):
    - vessel, transporter, por, fpd, marketing_person, nvocc_forwarder, shipper, consignee
    """
    errors = {}

    # Mandatory FK references
    mandatory_refs = {
        'client': (Client, 'Client'),
        'shipping_line': (ShippingLine, 'Shipping Line'),
        'pol': (Port, 'Port of Loading'),
        'pod': (Port, 'Port of Discharge'),
        'commodity': (Commodity, 'Commodity'),
    }

    for field, (model, label) in mandatory_refs.items():
        value = data.get(field)
        if value is not None:
            # value could be an ID (int) or a model instance
            pk = value.pk if hasattr(value, 'pk') else value
            if pk and not model.objects.filter(pk=pk).exists():
                errors[field] = [f'{label} with the given ID does not exist.']

    # Optional FK references
    optional_refs = {
        'vessel': (Vessel, 'Vessel'),
        'transporter': (Transporter, 'Transporter'),
        'por': (Port, 'Place of Receipt'),
        'fpd': (Port, 'Final Place of Delivery'),
        'marketing_person': (MarketingPerson, 'Marketing Person'),
        'nvocc_forwarder': (Forwarder, 'NVOCC/Forwarder'),
        'shipper': (Shipper, 'Shipper'),
        'consignee': (Consignee, 'Consignee'),
    }

    for field, (model, label) in optional_refs.items():
        value = data.get(field)
        if value is not None:
            pk = value.pk if hasattr(value, 'pk') else value
            if pk and not model.objects.filter(pk=pk).exists():
                errors[field] = [f'{label} with the given ID does not exist.']

    if errors:
        raise serializers.ValidationError(errors)

    return data


def validate_transhipment_legs(legs_data, existing_legs_count=0):
    """
    Validate transhipment legs data.

    Args:
        legs_data: List of dicts with keys: port, eta, connecting_vessel_voyage, etd
        existing_legs_count: Number of existing legs already on the booking.

    Raises:
        serializers.ValidationError with field-level errors.
    """
    errors = {}

    # Check max 4 total legs
    total_legs = existing_legs_count + len(legs_data)
    if total_legs > MAX_TRANSHIPMENT_LEGS:
        errors['transhipment_legs'] = [
            f'A maximum of {MAX_TRANSHIPMENT_LEGS} transhipment legs are allowed. '
            f'Currently {existing_legs_count} exist.'
        ]
        raise serializers.ValidationError(errors)

    # Validate each leg individually
    required_fields = ['port', 'eta', 'connecting_vessel_voyage', 'etd']
    for i, leg in enumerate(legs_data):
        # Check required fields
        for field in required_fields:
            if field not in leg or leg[field] is None or leg[field] == '':
                errors[f'legs[{i}].{field}'] = [
                    f'{field} is required for each transhipment leg.'
                ]

    if errors:
        raise serializers.ValidationError(errors)

    # Validate port references
    for i, leg in enumerate(legs_data):
        port = leg.get('port')
        if port is not None:
            port_id = port.pk if hasattr(port, 'pk') else port
            if port_id and not Port.objects.filter(pk=port_id).exists():
                errors[f'legs[{i}].port'] = [
                    'Port with the given ID does not exist.'
                ]

    if errors:
        raise serializers.ValidationError(errors)

    # Validate ETD > ETA within each leg
    for i, leg in enumerate(legs_data):
        eta = leg.get('eta')
        etd = leg.get('etd')
        if eta and etd and etd <= eta:
            errors[f'legs[{i}].etd'] = [
                'ETD must be strictly later than ETA at the same port.'
            ]

    if errors:
        raise serializers.ValidationError(errors)

    # Validate chronological ordering across legs
    for i in range(1, len(legs_data)):
        prev_etd = legs_data[i - 1].get('etd')
        curr_eta = legs_data[i].get('eta')
        if prev_etd and curr_eta and curr_eta < prev_etd:
            errors[f'legs[{i}].eta'] = [
                'ETA of this leg must be on or after the ETD of the preceding leg.'
            ]

    if errors:
        raise serializers.ValidationError(errors)

    return legs_data


def validate_transhipment_legs_chronology(all_legs):
    """
    Validate chronological ordering across all legs (existing + new) on a booking.
    Expects a list of leg dicts ordered by sequence, each with 'eta' and 'etd'.

    Args:
        all_legs: List of dicts with 'eta' and 'etd' keys, ordered by sequence.

    Raises:
        serializers.ValidationError if chronological order is violated.
    """
    errors = {}

    for i, leg in enumerate(all_legs):
        eta = leg.get('eta')
        etd = leg.get('etd')
        if eta and etd and etd <= eta:
            errors[f'legs[{i}].etd'] = [
                'ETD must be strictly later than ETA at the same port.'
            ]

    for i in range(1, len(all_legs)):
        prev_etd = all_legs[i - 1].get('etd')
        curr_eta = all_legs[i].get('eta')
        if prev_etd and curr_eta and curr_eta < prev_etd:
            errors[f'legs[{i}].eta'] = [
                'ETA of this leg must be on or after the ETD of the preceding leg.'
            ]

    if errors:
        raise serializers.ValidationError(errors)
