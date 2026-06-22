"""
Tests for the check_pending_bl Celery task.
"""

import datetime

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from bl.models import BillOfLading
from bl.tasks import check_pending_bl
from bookings.models import Booking
from dashboard.models import Alert
from master_data.models import (
    Client,
    Commodity,
    Consignee,
    Port,
    Shipper,
    ShippingLine,
)

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='taskuser', password='testpass123')


@pytest.fixture
def master_data(db):
    shipping_line = ShippingLine.objects.create(name='Maersk', code='MAEU')
    pol = Port.objects.create(name='Mumbai Port', code='INMUN', country='India')
    pod = Port.objects.create(name='Rotterdam Port', code='NLRTM', country='Netherlands')
    client_obj = Client.objects.create(name='Test Client', email='client@test.com')
    commodity = Commodity.objects.create(name='Electronics', hs_code='8542')
    shipper = Shipper.objects.create(name='Test Shipper', address='123 Ship St')
    consignee = Consignee.objects.create(name='Test Consignee', address='456 Con Ave')
    return {
        'shipping_line': shipping_line,
        'pol': pol,
        'pod': pod,
        'client': client_obj,
        'commodity': commodity,
        'shipper': shipper,
        'consignee': consignee,
    }


def _create_booking(master_data, user, status=Booking.Status.SHIPPED, etd_pol=None):
    today = datetime.date.today()
    return Booking.objects.create(
        booking_date=today,
        booking_validity_date=today,
        forwarding_window_start=today,
        forwarding_window_end=today,
        shipping_line=master_data['shipping_line'],
        pol=master_data['pol'],
        pod=master_data['pod'],
        client=master_data['client'],
        commodity=master_data['commodity'],
        cargo_type=Booking.CargoType.FCL,
        shipment_type='Export',
        stuffing_type='Factory',
        status=status,
        etd_pol=etd_pol,
        created_by=user,
    )


class TestCheckPendingBL:
    """Tests for the check_pending_bl Celery task."""

    def test_no_shipped_bookings_creates_no_alerts(self, user, master_data):
        """No shipped bookings means no alerts."""
        _create_booking(master_data, user, status=Booking.Status.BOOKED,
                        etd_pol=timezone.now() - datetime.timedelta(days=10))
        check_pending_bl()
        assert Alert.objects.count() == 0

    def test_shipped_booking_no_bl_etd_over_7_days_creates_missing_bl_alert(
        self, user, master_data
    ):
        """Shipped booking with no BL and ETD > 7 days ago creates MISSING_BL alert."""
        etd = timezone.now() - datetime.timedelta(days=10)
        booking = _create_booking(master_data, user, etd_pol=etd)

        check_pending_bl()

        assert Alert.objects.count() == 1
        alert = Alert.objects.first()
        assert alert.alert_type == Alert.AlertType.MISSING_BL
        assert alert.related_object_id == booking.pk
        assert alert.related_object_type == 'booking'
        assert alert.is_resolved is False
        assert booking.job_number in alert.message

    def test_shipped_booking_bl_in_draft_etd_over_7_days_creates_pending_bl_alert(
        self, user, master_data
    ):
        """Shipped booking with BL in DRAFT and ETD > 7 days ago creates PENDING_BL alert."""
        etd = timezone.now() - datetime.timedelta(days=10)
        booking = _create_booking(master_data, user, etd_pol=etd)
        BillOfLading.objects.create(
            booking=booking,
            bl_number='BL-TEST-001',
            bl_type=BillOfLading.BLType.LINE,
            status=BillOfLading.Status.DRAFT,
            container_number='CONT001',
            vessel_name='Ever Given',
            voyage_number='V001',
            shipper=master_data['shipper'],
            consignee=master_data['consignee'],
            created_by=user,
        )

        check_pending_bl()

        assert Alert.objects.count() == 1
        alert = Alert.objects.first()
        assert alert.alert_type == Alert.AlertType.PENDING_BL
        assert alert.related_object_id == booking.pk

    def test_shipped_booking_bl_submitted_no_alert(self, user, master_data):
        """Shipped booking with BL in SUBMITTED does not create an alert."""
        etd = timezone.now() - datetime.timedelta(days=10)
        booking = _create_booking(master_data, user, etd_pol=etd)
        BillOfLading.objects.create(
            booking=booking,
            bl_number='BL-TEST-002',
            bl_type=BillOfLading.BLType.LINE,
            status=BillOfLading.Status.SUBMITTED,
            container_number='CONT001',
            vessel_name='Ever Given',
            voyage_number='V001',
            shipper=master_data['shipper'],
            consignee=master_data['consignee'],
            created_by=user,
        )

        check_pending_bl()
        assert Alert.objects.count() == 0

    def test_shipped_booking_bl_released_no_alert(self, user, master_data):
        """Shipped booking with BL in RELEASED does not create an alert."""
        etd = timezone.now() - datetime.timedelta(days=10)
        booking = _create_booking(master_data, user, etd_pol=etd)
        BillOfLading.objects.create(
            booking=booking,
            bl_number='BL-TEST-003',
            bl_type=BillOfLading.BLType.DIRECT,
            status=BillOfLading.Status.RELEASED,
            container_number='CONT001',
            vessel_name='Ever Given',
            voyage_number='V001',
            shipper=master_data['shipper'],
            consignee=master_data['consignee'],
            created_by=user,
        )

        check_pending_bl()
        assert Alert.objects.count() == 0

    def test_shipped_booking_etd_less_than_7_days_no_alert(self, user, master_data):
        """Shipped booking with ETD less than 7 days ago does not create alert."""
        etd = timezone.now() - datetime.timedelta(days=3)
        _create_booking(master_data, user, etd_pol=etd)

        check_pending_bl()
        assert Alert.objects.count() == 0

    def test_no_duplicate_alerts_on_repeated_runs(self, user, master_data):
        """Running the task twice does not create duplicate alerts."""
        etd = timezone.now() - datetime.timedelta(days=10)
        _create_booking(master_data, user, etd_pol=etd)

        check_pending_bl()
        assert Alert.objects.count() == 1

        check_pending_bl()
        assert Alert.objects.count() == 1

    def test_resolved_alert_allows_new_alert_creation(self, user, master_data):
        """If a previous alert was resolved, a new one can be created."""
        etd = timezone.now() - datetime.timedelta(days=10)
        booking = _create_booking(master_data, user, etd_pol=etd)

        check_pending_bl()
        assert Alert.objects.count() == 1

        # Resolve the alert
        Alert.objects.filter(related_object_id=booking.pk).update(is_resolved=True)

        check_pending_bl()
        assert Alert.objects.filter(is_resolved=False).count() == 1
        assert Alert.objects.count() == 2

    def test_multiple_bookings_create_multiple_alerts(self, user, master_data):
        """Multiple qualifying bookings create separate alerts."""
        etd = timezone.now() - datetime.timedelta(days=10)
        _create_booking(master_data, user, etd_pol=etd)

        # Need a second port for the second booking to avoid conflict - actually
        # we can reuse since no unique constraint on these relationships
        _create_booking(master_data, user, etd_pol=etd)

        check_pending_bl()
        assert Alert.objects.count() == 2
