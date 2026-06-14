"""
Unit tests for bookings/validators.py

Tests cover:
- Date ordering validation
- HAZ conditional field validation
- Certificates validation
- Remarks length validation
- Master data referential integrity validation
"""

import datetime

import pytest
from rest_framework import serializers

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
    Forwarder,
    MarketingPerson,
    Port,
    Shipper,
    ShippingLine,
    Transporter,
    Vessel,
)


# ---------------------------------------------------------------------------
# validate_booking_dates tests
# ---------------------------------------------------------------------------


class TestValidateBookingDates:
    """Tests for validate_booking_dates validator."""

    def test_valid_dates_equal(self):
        """Validity date equal to booking date is valid."""
        data = {
            'booking_date': datetime.date(2024, 1, 15),
            'booking_validity_date': datetime.date(2024, 1, 15),
            'forwarding_window_start': datetime.date(2024, 2, 1),
            'forwarding_window_end': datetime.date(2024, 2, 1),
        }
        result = validate_booking_dates(data)
        assert result == data

    def test_valid_dates_after(self):
        """Validity date after booking date and window end after start."""
        data = {
            'booking_date': datetime.date(2024, 1, 15),
            'booking_validity_date': datetime.date(2024, 2, 15),
            'forwarding_window_start': datetime.date(2024, 3, 1),
            'forwarding_window_end': datetime.date(2024, 3, 31),
        }
        result = validate_booking_dates(data)
        assert result == data

    def test_validity_date_before_booking_date(self):
        """Validity date before booking date raises error."""
        data = {
            'booking_date': datetime.date(2024, 3, 15),
            'booking_validity_date': datetime.date(2024, 3, 10),
            'forwarding_window_start': datetime.date(2024, 4, 1),
            'forwarding_window_end': datetime.date(2024, 4, 30),
        }
        with pytest.raises(serializers.ValidationError) as exc_info:
            validate_booking_dates(data)
        errors = exc_info.value.detail
        assert 'booking_validity_date' in errors

    def test_forwarding_window_end_before_start(self):
        """Window end before start raises error."""
        data = {
            'booking_date': datetime.date(2024, 1, 1),
            'booking_validity_date': datetime.date(2024, 1, 31),
            'forwarding_window_start': datetime.date(2024, 5, 15),
            'forwarding_window_end': datetime.date(2024, 5, 1),
        }
        with pytest.raises(serializers.ValidationError) as exc_info:
            validate_booking_dates(data)
        errors = exc_info.value.detail
        assert 'forwarding_window_end' in errors

    def test_both_date_errors(self):
        """Both date ordering violations raise combined errors."""
        data = {
            'booking_date': datetime.date(2024, 6, 15),
            'booking_validity_date': datetime.date(2024, 6, 1),
            'forwarding_window_start': datetime.date(2024, 7, 20),
            'forwarding_window_end': datetime.date(2024, 7, 10),
        }
        with pytest.raises(serializers.ValidationError) as exc_info:
            validate_booking_dates(data)
        errors = exc_info.value.detail
        assert 'booking_validity_date' in errors
        assert 'forwarding_window_end' in errors

    def test_missing_dates_no_error(self):
        """Missing date fields don't trigger errors (mandatory check is separate)."""
        data = {
            'booking_date': None,
            'booking_validity_date': None,
            'forwarding_window_start': None,
            'forwarding_window_end': None,
        }
        result = validate_booking_dates(data)
        assert result == data


# ---------------------------------------------------------------------------
# validate_haz_fields tests
# ---------------------------------------------------------------------------


class TestValidateHazFields:
    """Tests for validate_haz_fields validator."""

    def test_haz_true_all_fields_present(self):
        """HAZ true with all fields populated passes."""
        data = {
            'is_haz': True,
            'haz_class': 'Class 3',
            'haz_uin': 'UN1234',
            'haz_group': 'PG II',
        }
        result = validate_haz_fields(data)
        assert result['haz_class'] == 'Class 3'
        assert result['haz_uin'] == 'UN1234'
        assert result['haz_group'] == 'PG II'

    def test_haz_true_missing_all_fields(self):
        """HAZ true with missing fields raises errors for all three."""
        data = {
            'is_haz': True,
            'haz_class': '',
            'haz_uin': '',
            'haz_group': '',
        }
        with pytest.raises(serializers.ValidationError) as exc_info:
            validate_haz_fields(data)
        errors = exc_info.value.detail
        assert 'haz_class' in errors
        assert 'haz_uin' in errors
        assert 'haz_group' in errors

    def test_haz_true_partial_fields(self):
        """HAZ true with some fields missing raises errors for missing ones."""
        data = {
            'is_haz': True,
            'haz_class': 'Class 6',
            'haz_uin': '',
            'haz_group': '',
        }
        with pytest.raises(serializers.ValidationError) as exc_info:
            validate_haz_fields(data)
        errors = exc_info.value.detail
        assert 'haz_class' not in errors
        assert 'haz_uin' in errors
        assert 'haz_group' in errors

    def test_haz_false_discards_values(self):
        """HAZ false discards any provided HAZ field values."""
        data = {
            'is_haz': False,
            'haz_class': 'Class 3',
            'haz_uin': 'UN1234',
            'haz_group': 'PG II',
        }
        result = validate_haz_fields(data)
        assert result['haz_class'] == ''
        assert result['haz_uin'] == ''
        assert result['haz_group'] == ''

    def test_haz_not_provided_defaults_false(self):
        """When is_haz is not in data, defaults to False behavior."""
        data = {
            'haz_class': 'Class 1',
            'haz_uin': 'UN9999',
            'haz_group': 'PG I',
        }
        result = validate_haz_fields(data)
        assert result['haz_class'] == ''
        assert result['haz_uin'] == ''
        assert result['haz_group'] == ''

    def test_haz_true_none_values_treated_as_missing(self):
        """HAZ true with None values treated as missing."""
        data = {
            'is_haz': True,
            'haz_class': None,
            'haz_uin': None,
            'haz_group': None,
        }
        with pytest.raises(serializers.ValidationError) as exc_info:
            validate_haz_fields(data)
        errors = exc_info.value.detail
        assert 'haz_class' in errors
        assert 'haz_uin' in errors
        assert 'haz_group' in errors


# ---------------------------------------------------------------------------
# validate_certificates tests
# ---------------------------------------------------------------------------


class TestValidateCertificates:
    """Tests for validate_certificates validator."""

    def test_valid_certificates(self):
        """A list of 1-5 strings is valid."""
        certs = ['ISO 9001', 'HACCP', 'GMP']
        result = validate_certificates(certs)
        assert result == certs

    def test_empty_list_valid(self):
        """Empty list is valid."""
        result = validate_certificates([])
        assert result == []

    def test_none_value_valid(self):
        """None is valid (field is optional)."""
        result = validate_certificates(None)
        assert result is None

    def test_max_five_entries(self):
        """Exactly 5 entries is valid."""
        certs = ['A', 'B', 'C', 'D', 'E']
        result = validate_certificates(certs)
        assert result == certs

    def test_exceeds_five_entries(self):
        """More than 5 entries raises error."""
        certs = ['A', 'B', 'C', 'D', 'E', 'F']
        with pytest.raises(serializers.ValidationError) as exc_info:
            validate_certificates(certs)
        errors = exc_info.value.detail
        assert 'certificates' in errors

    def test_not_a_list(self):
        """Non-list value raises error."""
        with pytest.raises(serializers.ValidationError) as exc_info:
            validate_certificates('ISO 9001')
        errors = exc_info.value.detail
        assert 'certificates' in errors

    def test_non_string_entry(self):
        """Non-string entry in list raises error."""
        certs = ['ISO 9001', 123, 'GMP']
        with pytest.raises(serializers.ValidationError) as exc_info:
            validate_certificates(certs)
        errors = exc_info.value.detail
        assert 'certificates' in errors
        assert 'index 1' in errors['certificates'][0]

    def test_dict_is_not_valid(self):
        """Dict is not a valid certificates value."""
        with pytest.raises(serializers.ValidationError) as exc_info:
            validate_certificates({'cert': 'ISO'})
        errors = exc_info.value.detail
        assert 'certificates' in errors


# ---------------------------------------------------------------------------
# validate_remarks tests
# ---------------------------------------------------------------------------


class TestValidateRemarks:
    """Tests for validate_remarks validator."""

    def test_valid_short_remarks(self):
        """Short remarks pass validation."""
        result = validate_remarks('This is a short remark.')
        assert result == 'This is a short remark.'

    def test_valid_exactly_2000_chars(self):
        """Exactly 2000 characters is valid."""
        remarks = 'x' * 2000
        result = validate_remarks(remarks)
        assert result == remarks

    def test_exceeds_2000_chars(self):
        """More than 2000 characters raises error."""
        remarks = 'x' * 2001
        with pytest.raises(serializers.ValidationError) as exc_info:
            validate_remarks(remarks)
        errors = exc_info.value.detail
        assert 'remarks' in errors

    def test_empty_string_valid(self):
        """Empty string is valid."""
        result = validate_remarks('')
        assert result == ''

    def test_none_valid(self):
        """None is valid (field is optional)."""
        result = validate_remarks(None)
        assert result is None


# ---------------------------------------------------------------------------
# validate_master_data_references tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestValidateMasterDataReferences:
    """Tests for validate_master_data_references validator."""

    @pytest.fixture
    def master_data(self):
        """Create master data records for testing."""
        client = Client.objects.create(name='Test Client')
        shipping_line = ShippingLine.objects.create(name='Test Shipping Line')
        pol = Port.objects.create(name='Mumbai Port', code='INMUN')
        pod = Port.objects.create(name='Singapore Port', code='SGSIN')
        commodity = Commodity.objects.create(name='Electronics')
        vessel = Vessel.objects.create(name='MV Test', shipping_line=shipping_line)
        transporter = Transporter.objects.create(name='Test Transporter')
        por = Port.objects.create(name='Delhi ICD', code='INDEL')
        fpd = Port.objects.create(name='Tokyo Port', code='JPTYO')
        marketing_person = MarketingPerson.objects.create(name='Sales Rep')
        forwarder = Forwarder.objects.create(name='Test Forwarder')
        shipper = Shipper.objects.create(name='Test Shipper')
        consignee = Consignee.objects.create(name='Test Consignee')

        return {
            'client': client,
            'shipping_line': shipping_line,
            'pol': pol,
            'pod': pod,
            'commodity': commodity,
            'vessel': vessel,
            'transporter': transporter,
            'por': por,
            'fpd': fpd,
            'marketing_person': marketing_person,
            'nvocc_forwarder': forwarder,
            'shipper': shipper,
            'consignee': consignee,
        }

    def test_all_valid_references_with_ids(self, master_data):
        """All FK IDs exist in master data — passes."""
        data = {
            'client': master_data['client'].pk,
            'shipping_line': master_data['shipping_line'].pk,
            'pol': master_data['pol'].pk,
            'pod': master_data['pod'].pk,
            'commodity': master_data['commodity'].pk,
            'vessel': master_data['vessel'].pk,
            'transporter': master_data['transporter'].pk,
            'por': master_data['por'].pk,
            'fpd': master_data['fpd'].pk,
            'marketing_person': master_data['marketing_person'].pk,
            'nvocc_forwarder': master_data['nvocc_forwarder'].pk,
            'shipper': master_data['shipper'].pk,
            'consignee': master_data['consignee'].pk,
        }
        result = validate_master_data_references(data)
        assert result == data

    def test_all_valid_references_with_instances(self, master_data):
        """Model instances as values — passes."""
        data = {
            'client': master_data['client'],
            'shipping_line': master_data['shipping_line'],
            'pol': master_data['pol'],
            'pod': master_data['pod'],
            'commodity': master_data['commodity'],
        }
        result = validate_master_data_references(data)
        assert result == data

    def test_invalid_mandatory_client(self, master_data):
        """Non-existent client ID raises error."""
        data = {
            'client': 99999,
            'shipping_line': master_data['shipping_line'].pk,
            'pol': master_data['pol'].pk,
            'pod': master_data['pod'].pk,
            'commodity': master_data['commodity'].pk,
        }
        with pytest.raises(serializers.ValidationError) as exc_info:
            validate_master_data_references(data)
        errors = exc_info.value.detail
        assert 'client' in errors

    def test_invalid_mandatory_shipping_line(self, master_data):
        """Non-existent shipping_line ID raises error."""
        data = {
            'client': master_data['client'].pk,
            'shipping_line': 99999,
            'pol': master_data['pol'].pk,
            'pod': master_data['pod'].pk,
            'commodity': master_data['commodity'].pk,
        }
        with pytest.raises(serializers.ValidationError) as exc_info:
            validate_master_data_references(data)
        errors = exc_info.value.detail
        assert 'shipping_line' in errors

    def test_invalid_optional_vessel(self, master_data):
        """Non-existent optional vessel ID raises error."""
        data = {
            'client': master_data['client'].pk,
            'shipping_line': master_data['shipping_line'].pk,
            'pol': master_data['pol'].pk,
            'pod': master_data['pod'].pk,
            'commodity': master_data['commodity'].pk,
            'vessel': 99999,
        }
        with pytest.raises(serializers.ValidationError) as exc_info:
            validate_master_data_references(data)
        errors = exc_info.value.detail
        assert 'vessel' in errors

    def test_optional_fields_none_is_valid(self, master_data):
        """Optional FK fields set to None don't trigger errors."""
        data = {
            'client': master_data['client'].pk,
            'shipping_line': master_data['shipping_line'].pk,
            'pol': master_data['pol'].pk,
            'pod': master_data['pod'].pk,
            'commodity': master_data['commodity'].pk,
            'vessel': None,
            'transporter': None,
            'por': None,
            'fpd': None,
            'marketing_person': None,
            'nvocc_forwarder': None,
            'shipper': None,
            'consignee': None,
        }
        result = validate_master_data_references(data)
        assert result == data

    def test_multiple_invalid_references(self, master_data):
        """Multiple invalid references reported in one error."""
        data = {
            'client': 99999,
            'shipping_line': 99999,
            'pol': master_data['pol'].pk,
            'pod': 99999,
            'commodity': master_data['commodity'].pk,
            'vessel': 99999,
        }
        with pytest.raises(serializers.ValidationError) as exc_info:
            validate_master_data_references(data)
        errors = exc_info.value.detail
        assert 'client' in errors
        assert 'shipping_line' in errors
        assert 'pod' in errors
        assert 'vessel' in errors

    def test_missing_mandatory_fields_not_checked(self, master_data):
        """Fields not present in data dict are not validated (separate mandatory check)."""
        data = {
            'client': master_data['client'].pk,
            'shipping_line': master_data['shipping_line'].pk,
            # pol, pod, commodity not in data
        }
        # Should not raise — missing fields are handled by mandatory field check
        result = validate_master_data_references(data)
        assert result == data
