"""
Tests for Booking status extension (new transitions, stuffing prerequisite for SHIPPED).
Task 25.10.
"""

import datetime

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import serializers

from bookings.models import Booking, Container
from bookings.services import BookingService, validate_booking_status_transition, validate_can_ship
from master_data.models import Client, Commodity, ContainerType, Port, ShippingLine

User = get_user_model()


@pytest.fixture
def ops_user(db):
    user = User.objects.create_user(username='ops_user', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Operations')
    user.groups.add(group)
    return user


@pytest.fixture
def master_data(db):
    shipping_line = ShippingLine.objects.create(name='Maersk', code='MAEU')
    pol = Port.objects.create(name='Mumbai Port', code='INMUN', country='India')
    pod = Port.objects.create(name='Rotterdam Port', code='NLRTM', country='Netherlands')
    client = Client.objects.create(name='Test Client', email='client@test.com')
    commodity = Commodity.objects.create(name='Electronics', hs_code='8542')
    container_type = ContainerType.objects.create(name='Dry', code='DRY')
    return {
        'shipping_line': shipping_line,
        'pol': pol,
        'pod': pod,
        'client': client,
        'commodity': commodity,
        'container_type': container_type,
    }


@pytest.fixture
def pending_booking(master_data, ops_user):
    """Create a PENDING booking."""
    today = datetime.date.today()
    return Booking.objects.create(
        status=Booking.Status.PENDING,
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
        created_by=ops_user,
    )


@pytest.mark.django_db
class TestBookingStatusTransitions:
    """Tests for valid booking status transitions."""

    def test_pending_to_booked(self, pending_booking, ops_user):
        """PENDING -> BOOKED is valid."""
        booking = BookingService.change_status(pending_booking.pk, 'BOOKED', ops_user)
        assert booking.status == Booking.Status.BOOKED

    def test_booked_to_stuffing(self, pending_booking, ops_user):
        """BOOKED -> STUFFING is valid."""
        BookingService.change_status(pending_booking.pk, 'BOOKED', ops_user)
        booking = BookingService.change_status(pending_booking.pk, 'STUFFING', ops_user)
        assert booking.status == Booking.Status.STUFFING

    def test_stuffing_to_shipped_all_stuffed(self, pending_booking, master_data, ops_user):
        """STUFFING -> SHIPPED when all containers are stuffed."""
        BookingService.change_status(pending_booking.pk, 'BOOKED', ops_user)
        BookingService.change_status(pending_booking.pk, 'STUFFING', ops_user)

        # Add a stuffed container
        Container.objects.create(
            booking=pending_booking,
            container_type=master_data['container_type'],
            container_size='20FT',
            container_count=1,
            stuffing_status='STUFFED',
        )

        booking = BookingService.change_status(pending_booking.pk, 'SHIPPED', ops_user)
        assert booking.status == Booking.Status.SHIPPED

    def test_shipped_to_completed(self, pending_booking, master_data, ops_user):
        """SHIPPED -> COMPLETED is valid."""
        BookingService.change_status(pending_booking.pk, 'BOOKED', ops_user)
        BookingService.change_status(pending_booking.pk, 'STUFFING', ops_user)

        Container.objects.create(
            booking=pending_booking,
            container_type=master_data['container_type'],
            container_size='20FT',
            container_count=1,
            stuffing_status='STUFFED',
        )
        BookingService.change_status(pending_booking.pk, 'SHIPPED', ops_user)
        booking = BookingService.change_status(pending_booking.pk, 'COMPLETED', ops_user)
        assert booking.status == Booking.Status.COMPLETED


@pytest.mark.django_db
class TestInvalidBookingTransitions:
    """Tests for rejected booking status transitions."""

    def test_pending_to_shipped_rejected(self, pending_booking, ops_user):
        """PENDING -> SHIPPED is not allowed."""
        with pytest.raises(serializers.ValidationError):
            BookingService.change_status(pending_booking.pk, 'SHIPPED', ops_user)

    def test_backward_transition_rejected(self, pending_booking, ops_user):
        """BOOKED -> PENDING is not allowed."""
        BookingService.change_status(pending_booking.pk, 'BOOKED', ops_user)
        with pytest.raises(serializers.ValidationError):
            BookingService.change_status(pending_booking.pk, 'PENDING', ops_user)

    def test_skip_status_rejected(self, pending_booking, ops_user):
        """PENDING -> STUFFING is not allowed (must go through BOOKED)."""
        with pytest.raises(serializers.ValidationError):
            BookingService.change_status(pending_booking.pk, 'STUFFING', ops_user)


@pytest.mark.django_db
class TestStuffingPrerequisiteForShipped:
    """Tests for stuffing requirement before SHIPPED transition."""

    def test_shipped_rejected_with_pending_containers(self, pending_booking, master_data, ops_user):
        """Cannot transition to SHIPPED if any container has stuffing_status PENDING."""
        BookingService.change_status(pending_booking.pk, 'BOOKED', ops_user)
        BookingService.change_status(pending_booking.pk, 'STUFFING', ops_user)

        # Add a PENDING container
        Container.objects.create(
            booking=pending_booking,
            container_type=master_data['container_type'],
            container_size='20FT',
            container_count=1,
            stuffing_status='PENDING',
        )

        with pytest.raises(serializers.ValidationError) as exc_info:
            BookingService.change_status(pending_booking.pk, 'SHIPPED', ops_user)
        assert 'STUFFED' in str(exc_info.value.detail['status'])

    def test_shipped_rejected_with_no_containers(self, pending_booking, ops_user):
        """Cannot transition to SHIPPED if booking has no containers."""
        BookingService.change_status(pending_booking.pk, 'BOOKED', ops_user)
        BookingService.change_status(pending_booking.pk, 'STUFFING', ops_user)

        with pytest.raises(serializers.ValidationError) as exc_info:
            BookingService.change_status(pending_booking.pk, 'SHIPPED', ops_user)
        assert 'no containers' in str(exc_info.value.detail['status']).lower()

    def test_shipped_rejected_mixed_containers(self, pending_booking, master_data, ops_user):
        """Cannot transition to SHIPPED if some containers are PENDING and others are STUFFED."""
        BookingService.change_status(pending_booking.pk, 'BOOKED', ops_user)
        BookingService.change_status(pending_booking.pk, 'STUFFING', ops_user)

        Container.objects.create(
            booking=pending_booking,
            container_type=master_data['container_type'],
            container_size='20FT',
            container_count=1,
            stuffing_status='STUFFED',
        )
        Container.objects.create(
            booking=pending_booking,
            container_type=master_data['container_type'],
            container_size='40FT',
            container_count=1,
            stuffing_status='PENDING',
        )

        with pytest.raises(serializers.ValidationError):
            BookingService.change_status(pending_booking.pk, 'SHIPPED', ops_user)
