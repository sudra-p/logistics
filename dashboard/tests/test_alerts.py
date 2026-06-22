"""
Tests for the dashboard alerts endpoint.
"""

import datetime

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from bl.models import BillOfLading
from bookings.models import Booking
from master_data.models import (
    Client,
    Commodity,
    Consignee,
    Port,
    Shipper,
    ShippingLine,
)
from proforma.models import ProformaInvoice

User = get_user_model()

ALERTS_URL = '/api/dashboard/alerts/'


@pytest.fixture
def authenticated_client(db):
    """Create an authenticated user and API client."""
    user = User.objects.create_user(username='testuser', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Operations')
    user.groups.add(group)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def master_data(db):
    """Create required master data for bookings and PIs."""
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


def _create_booking(master_data, user, booking_status=Booking.Status.PENDING, etd_pol=None):
    """Helper to create a booking with required fields."""
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
        status=booking_status,
        etd_pol=etd_pol,
        created_by=user,
    )


def _create_pi(master_data, user, pi_status=ProformaInvoice.Status.DRAFT):
    """Helper to create a proforma invoice."""
    today = datetime.date.today()
    pi = ProformaInvoice(
        date=today,
        customer=master_data['client'],
        currency=ProformaInvoice.Currency.USD,
        payment_terms='Net 30',
        expected_shipment_date=today,
        total_amount=1000,
        status=pi_status,
        created_by=user,
    )
    pi.save()
    return pi


class TestAlertsEndpoint:
    """Tests for GET /api/dashboard/alerts/"""

    def test_unauthenticated_returns_401(self, db):
        client = APIClient()
        response = client.get(ALERTS_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_database_returns_empty_alerts(self, authenticated_client):
        client, user = authenticated_client
        response = client.get(ALERTS_URL)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['payment_overdue'] == []
        assert data['shipment_delay'] == []
        assert data['missing_bl'] == []

    def test_payment_overdue_pi_in_payment_pending_over_30_days(
        self, authenticated_client, master_data
    ):
        client, user = authenticated_client
        pi = _create_pi(master_data, user, ProformaInvoice.Status.PAYMENT_PENDING)
        # Manually set updated_at to 35 days ago
        old_date = timezone.now() - datetime.timedelta(days=35)
        ProformaInvoice.objects.filter(pk=pi.pk).update(updated_at=old_date)

        response = client.get(ALERTS_URL)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data['payment_overdue']) == 1
        alert = data['payment_overdue'][0]
        assert alert['type'] == 'payment_overdue'
        assert alert['pi_number'] == pi.pi_number
        assert alert['customer_name'] == 'Test Client'
        assert alert['days_overdue'] >= 35

    def test_payment_overdue_pi_less_than_30_days_not_included(
        self, authenticated_client, master_data
    ):
        client, user = authenticated_client
        pi = _create_pi(master_data, user, ProformaInvoice.Status.PAYMENT_PENDING)
        # updated_at is now (just created) which is less than 30 days ago
        response = client.get(ALERTS_URL)
        data = response.json()
        assert len(data['payment_overdue']) == 0

    def test_payment_overdue_only_payment_pending_status(
        self, authenticated_client, master_data
    ):
        client, user = authenticated_client
        # Create PI with DRAFT status (not PAYMENT_PENDING)
        pi = _create_pi(master_data, user, ProformaInvoice.Status.DRAFT)
        old_date = timezone.now() - datetime.timedelta(days=35)
        ProformaInvoice.objects.filter(pk=pi.pk).update(updated_at=old_date)

        response = client.get(ALERTS_URL)
        data = response.json()
        assert len(data['payment_overdue']) == 0

    def test_shipment_delay_etd_passed_not_shipped(
        self, authenticated_client, master_data
    ):
        client, user = authenticated_client
        past_etd = timezone.now() - datetime.timedelta(days=5)
        booking = _create_booking(
            master_data, user, Booking.Status.BOOKED, etd_pol=past_etd
        )

        response = client.get(ALERTS_URL)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data['shipment_delay']) == 1
        alert = data['shipment_delay'][0]
        assert alert['type'] == 'shipment_delay'
        assert alert['job_number'] == booking.job_number
        assert alert['customer_name'] == 'Test Client'

    def test_shipment_delay_etd_not_passed_not_included(
        self, authenticated_client, master_data
    ):
        client, user = authenticated_client
        future_etd = timezone.now() + datetime.timedelta(days=5)
        _create_booking(
            master_data, user, Booking.Status.BOOKED, etd_pol=future_etd
        )

        response = client.get(ALERTS_URL)
        data = response.json()
        assert len(data['shipment_delay']) == 0

    def test_shipment_delay_shipped_status_not_included(
        self, authenticated_client, master_data
    ):
        client, user = authenticated_client
        past_etd = timezone.now() - datetime.timedelta(days=5)
        _create_booking(
            master_data, user, Booking.Status.SHIPPED, etd_pol=past_etd
        )

        response = client.get(ALERTS_URL)
        data = response.json()
        assert len(data['shipment_delay']) == 0

    def test_shipment_delay_completed_status_not_included(
        self, authenticated_client, master_data
    ):
        client, user = authenticated_client
        past_etd = timezone.now() - datetime.timedelta(days=5)
        _create_booking(
            master_data, user, Booking.Status.COMPLETED, etd_pol=past_etd
        )

        response = client.get(ALERTS_URL)
        data = response.json()
        assert len(data['shipment_delay']) == 0

    def test_missing_bl_shipped_booking_without_bl(
        self, authenticated_client, master_data
    ):
        client, user = authenticated_client
        booking = _create_booking(master_data, user, Booking.Status.SHIPPED)

        response = client.get(ALERTS_URL)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data['missing_bl']) == 1
        alert = data['missing_bl'][0]
        assert alert['type'] == 'missing_bl'
        assert alert['job_number'] == booking.job_number
        assert alert['customer_name'] == 'Test Client'

    def test_missing_bl_shipped_booking_with_bl_not_included(
        self, authenticated_client, master_data
    ):
        client, user = authenticated_client
        booking = _create_booking(master_data, user, Booking.Status.SHIPPED)
        BillOfLading.objects.create(
            booking=booking,
            bl_number='BL-001',
            bl_type=BillOfLading.BLType.LINE,
            status=BillOfLading.Status.DRAFT,
            container_number='CONT001',
            vessel_name='Ever Given',
            voyage_number='V001',
            shipper=master_data['shipper'],
            consignee=master_data['consignee'],
            created_by=user,
        )

        response = client.get(ALERTS_URL)
        data = response.json()
        assert len(data['missing_bl']) == 0

    def test_missing_bl_non_shipped_booking_not_included(
        self, authenticated_client, master_data
    ):
        client, user = authenticated_client
        # BOOKED booking without BL should NOT trigger missing_bl alert
        _create_booking(master_data, user, Booking.Status.BOOKED)

        response = client.get(ALERTS_URL)
        data = response.json()
        assert len(data['missing_bl']) == 0

    def test_multiple_alerts_combined(
        self, authenticated_client, master_data
    ):
        client, user = authenticated_client

        # Create overdue PI
        pi = _create_pi(master_data, user, ProformaInvoice.Status.PAYMENT_PENDING)
        old_date = timezone.now() - datetime.timedelta(days=40)
        ProformaInvoice.objects.filter(pk=pi.pk).update(updated_at=old_date)

        # Create delayed shipment
        past_etd = timezone.now() - datetime.timedelta(days=3)
        _create_booking(master_data, user, Booking.Status.STUFFING, etd_pol=past_etd)

        # Create shipped booking without BL
        _create_booking(master_data, user, Booking.Status.SHIPPED)

        response = client.get(ALERTS_URL)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data['payment_overdue']) == 1
        assert len(data['shipment_delay']) == 1
        assert len(data['missing_bl']) == 1


from dashboard.models import Alert

DISMISS_URL = '/api/alerts/{id}/dismiss/'


class TestAlertDismissEndpoint:
    """Tests for PATCH /api/alerts/{id}/dismiss/"""

    def test_unauthenticated_returns_401(self, db):
        alert = Alert.objects.create(
            alert_type=Alert.AlertType.MISSING_BL,
            message='Test alert',
        )
        client = APIClient()
        response = client.patch(DISMISS_URL.format(id=alert.pk))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_dismiss_sets_is_read_and_is_resolved(self, authenticated_client):
        client, user = authenticated_client
        alert = Alert.objects.create(
            alert_type=Alert.AlertType.MISSING_BL,
            message='Missing BL for booking',
            is_read=False,
            is_resolved=False,
        )

        response = client.patch(DISMISS_URL.format(id=alert.pk))
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['is_read'] is True
        assert data['is_resolved'] is True

        # Verify database state
        alert.refresh_from_db()
        assert alert.is_read is True
        assert alert.is_resolved is True

    def test_dismiss_returns_full_alert_data(self, authenticated_client):
        client, user = authenticated_client
        alert = Alert.objects.create(
            alert_type=Alert.AlertType.PAYMENT_OVERDUE,
            message='Payment overdue for PI-202601-0001',
            related_object_id=42,
            related_object_type='ProformaInvoice',
            is_read=False,
            is_resolved=False,
        )

        response = client.patch(DISMISS_URL.format(id=alert.pk))
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['id'] == alert.pk
        assert data['alert_type'] == 'PAYMENT_OVERDUE'
        assert data['message'] == 'Payment overdue for PI-202601-0001'
        assert data['related_object_id'] == 42
        assert data['related_object_type'] == 'ProformaInvoice'
        assert data['is_read'] is True
        assert data['is_resolved'] is True
        assert 'created_at' in data
        assert 'updated_at' in data

    def test_dismiss_nonexistent_alert_returns_404(self, authenticated_client):
        client, user = authenticated_client
        response = client.patch(DISMISS_URL.format(id=99999))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_dismiss_already_dismissed_alert_is_idempotent(self, authenticated_client):
        client, user = authenticated_client
        alert = Alert.objects.create(
            alert_type=Alert.AlertType.SHIPMENT_DELAY,
            message='Shipment delayed',
            is_read=True,
            is_resolved=True,
        )

        response = client.patch(DISMISS_URL.format(id=alert.pk))
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['is_read'] is True
        assert data['is_resolved'] is True

    def test_dismiss_only_affects_target_alert(self, authenticated_client):
        client, user = authenticated_client
        alert1 = Alert.objects.create(
            alert_type=Alert.AlertType.MISSING_BL,
            message='Alert 1',
            is_read=False,
            is_resolved=False,
        )
        alert2 = Alert.objects.create(
            alert_type=Alert.AlertType.PENDING_BL,
            message='Alert 2',
            is_read=False,
            is_resolved=False,
        )

        response = client.patch(DISMISS_URL.format(id=alert1.pk))
        assert response.status_code == status.HTTP_200_OK

        # alert2 should remain unaffected
        alert2.refresh_from_db()
        assert alert2.is_read is False
        assert alert2.is_resolved is False
