"""Tests for booking models and constraints."""

import pytest
from datetime import date, datetime, timedelta, timezone
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from bookings.models import (
    Booking,
    BookingStatusHistory,
    CommunicationLog,
    Container,
    TranshipmentLeg,
    generate_job_number,
)
from master_data.models import (
    Client,
    Commodity,
    ContainerType,
    Port,
    ShippingLine,
)

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='testops', password='testpass123')


@pytest.fixture
def master_data(db):
    """Create required master data for booking creation."""
    client = Client.objects.create(name='Test Client')
    shipping_line = ShippingLine.objects.create(name='Test Line', code='TST')
    pol = Port.objects.create(name='Mumbai', code='INMUN')
    pod = Port.objects.create(name='Rotterdam', code='NLRTM')
    commodity = Commodity.objects.create(name='Electronics')
    container_type = ContainerType.objects.create(name='Standard', code='STD')
    return {
        'client': client,
        'shipping_line': shipping_line,
        'pol': pol,
        'pod': pod,
        'commodity': commodity,
        'container_type': container_type,
    }


@pytest.fixture
def booking(user, master_data):
    """Create a valid booking."""
    return Booking.objects.create(
        booking_date=date.today(),
        booking_validity_date=date.today() + timedelta(days=30),
        forwarding_window_start=date.today(),
        forwarding_window_end=date.today() + timedelta(days=14),
        shipping_line=master_data['shipping_line'],
        pol=master_data['pol'],
        pod=master_data['pod'],
        client=master_data['client'],
        commodity=master_data['commodity'],
        cargo_type=Booking.CargoType.FCL,
        shipment_type='Export',
        stuffing_type='Factory',
        created_by=user,
    )


@pytest.mark.django_db
class TestBookingModel:
    def test_booking_creation_generates_job_number(self, booking):
        assert booking.job_number.startswith('JOB-')
        assert len(booking.job_number) == 10  # JOB-000001

    def test_booking_job_number_is_unique(self, booking, user, master_data):
        booking2 = Booking.objects.create(
            booking_date=date.today(),
            booking_validity_date=date.today() + timedelta(days=30),
            forwarding_window_start=date.today(),
            forwarding_window_end=date.today() + timedelta(days=14),
            shipping_line=master_data['shipping_line'],
            pol=master_data['pol'],
            pod=master_data['pod'],
            client=master_data['client'],
            commodity=master_data['commodity'],
            cargo_type=Booking.CargoType.LCL,
            shipment_type='Export',
            stuffing_type='Factory',
            created_by=user,
        )
        assert booking.job_number != booking2.job_number

    def test_booking_default_status_is_pending(self, booking):
        assert booking.status == Booking.Status.PENDING

    def test_booking_str_representation(self, booking):
        assert booking.job_number in str(booking)

    def test_booking_status_choices(self):
        assert Booking.Status.PENDING == 'PENDING'
        assert Booking.Status.DO_BOOKING_EDIT == 'DO_BOOKING_EDIT'
        assert Booking.Status.COMPLETED == 'COMPLETED'

    def test_booking_cargo_type_choices(self):
        assert Booking.CargoType.FCL == 'FCL'
        assert Booking.CargoType.LCL == 'LCL'

    def test_booking_freight_terms_choices(self):
        assert Booking.FreightTerms.PREPAID == 'PREPAID'
        assert Booking.FreightTerms.COLLECT == 'COLLECT'

    def test_booking_indexes_count(self):
        assert len(Booking._meta.indexes) == 9


@pytest.mark.django_db
class TestContainerModel:
    def test_container_creation(self, booking, master_data):
        container = Container.objects.create(
            booking=booking,
            container_type=master_data['container_type'],
            container_size=Container.Size.FT_20,
            container_count=5,
        )
        assert container.container_count == 5
        assert container.container_size == '20FT'

    def test_container_size_choices(self):
        assert Container.Size.FT_20 == '20FT'
        assert Container.Size.FT_40 == '40FT'
        assert Container.Size.FT_40_HC == '40FT_HC'
        assert Container.Size.FT_45 == '45FT'

    def test_container_cascade_delete(self, booking, master_data):
        Container.objects.create(
            booking=booking,
            container_type=master_data['container_type'],
            container_size=Container.Size.FT_40,
            container_count=2,
        )
        booking_id = booking.id
        booking.delete()
        assert not Container.objects.filter(booking_id=booking_id).exists()


@pytest.mark.django_db
class TestTranshipmentLegModel:
    def test_transhipment_leg_creation(self, booking, master_data):
        now = datetime.now(tz=timezone.utc)
        leg = TranshipmentLeg.objects.create(
            booking=booking,
            sequence=1,
            port=master_data['pol'],
            eta=now,
            etd=now + timedelta(hours=12),
            connecting_vessel_voyage='VESSEL-V001',
        )
        assert leg.sequence == 1

    def test_transhipment_leg_unique_together(self, booking, master_data):
        now = datetime.now(tz=timezone.utc)
        TranshipmentLeg.objects.create(
            booking=booking,
            sequence=1,
            port=master_data['pol'],
            eta=now,
            etd=now + timedelta(hours=12),
            connecting_vessel_voyage='VESSEL-V001',
        )
        with pytest.raises(IntegrityError):
            TranshipmentLeg.objects.create(
                booking=booking,
                sequence=1,
                port=master_data['pod'],
                eta=now + timedelta(days=1),
                etd=now + timedelta(days=1, hours=12),
                connecting_vessel_voyage='VESSEL-V002',
            )

    def test_transhipment_leg_ordering(self, booking, master_data):
        now = datetime.now(tz=timezone.utc)
        TranshipmentLeg.objects.create(
            booking=booking,
            sequence=2,
            port=master_data['pod'],
            eta=now + timedelta(days=1),
            etd=now + timedelta(days=1, hours=12),
            connecting_vessel_voyage='VESSEL-V002',
        )
        TranshipmentLeg.objects.create(
            booking=booking,
            sequence=1,
            port=master_data['pol'],
            eta=now,
            etd=now + timedelta(hours=12),
            connecting_vessel_voyage='VESSEL-V001',
        )
        legs = list(booking.transhipment_legs.all())
        assert legs[0].sequence == 1
        assert legs[1].sequence == 2


@pytest.mark.django_db
class TestBookingStatusHistoryModel:
    def test_status_history_creation(self, booking, user):
        history = BookingStatusHistory.objects.create(
            booking=booking,
            previous_status=Booking.Status.PENDING,
            new_status=Booking.Status.DO_BOOKING_EDIT,
            changed_by=user,
        )
        assert history.previous_status == 'PENDING'
        assert history.new_status == 'DO_BOOKING_EDIT'
        assert history.changed_at is not None


@pytest.mark.django_db
class TestCommunicationLogModel:
    def test_communication_log_creation(self, booking):
        log = CommunicationLog.objects.create(
            booking=booking,
            email_type='booking_confirmation',
            recipients=['client@example.com', 'ops@company.com'],
            status='sent',
            sent_at=datetime.now(tz=timezone.utc),
        )
        assert log.email_type == 'booking_confirmation'
        assert len(log.recipients) == 2
        assert log.created_at is not None


@pytest.mark.django_db
class TestGenerateJobNumber:
    def test_generates_sequential_numbers(self, user, master_data):
        b1 = Booking.objects.create(
            booking_date=date.today(),
            booking_validity_date=date.today() + timedelta(days=30),
            forwarding_window_start=date.today(),
            forwarding_window_end=date.today() + timedelta(days=14),
            shipping_line=master_data['shipping_line'],
            pol=master_data['pol'],
            pod=master_data['pod'],
            client=master_data['client'],
            commodity=master_data['commodity'],
            cargo_type=Booking.CargoType.FCL,
            shipment_type='Export',
            stuffing_type='Factory',
            created_by=user,
        )
        b2 = Booking.objects.create(
            booking_date=date.today(),
            booking_validity_date=date.today() + timedelta(days=30),
            forwarding_window_start=date.today(),
            forwarding_window_end=date.today() + timedelta(days=14),
            shipping_line=master_data['shipping_line'],
            pol=master_data['pol'],
            pod=master_data['pod'],
            client=master_data['client'],
            commodity=master_data['commodity'],
            cargo_type=Booking.CargoType.FCL,
            shipment_type='Export',
            stuffing_type='Factory',
            created_by=user,
        )
        # Extract numeric parts
        num1 = int(b1.job_number.split('-')[1])
        num2 = int(b2.job_number.split('-')[1])
        assert num2 > num1

    def test_job_number_format(self, user, master_data):
        booking = Booking.objects.create(
            booking_date=date.today(),
            booking_validity_date=date.today() + timedelta(days=30),
            forwarding_window_start=date.today(),
            forwarding_window_end=date.today() + timedelta(days=14),
            shipping_line=master_data['shipping_line'],
            pol=master_data['pol'],
            pod=master_data['pod'],
            client=master_data['client'],
            commodity=master_data['commodity'],
            cargo_type=Booking.CargoType.FCL,
            shipment_type='Export',
            stuffing_type='Factory',
            created_by=user,
        )
        assert booking.job_number.startswith('JOB-')
        # Numeric portion should be 6 digits zero-padded
        numeric_part = booking.job_number[4:]
        assert len(numeric_part) == 6
        assert numeric_part.isdigit()
