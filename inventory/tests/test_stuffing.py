"""
Tests for stuffing action.
Task 25.6: Test successful deduction, insufficient stock rejection,
atomicity (no partial deductions), duplicate stuffing rejection.
"""

import datetime

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.exceptions import ValidationError

from bookings.models import Booking, Container
from inventory.models import StockItem
from inventory.services import StockService
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
def booking_with_container(master_data, ops_user):
    """Create a booking with a pending container."""
    today = datetime.date.today()
    booking = Booking.objects.create(
        status=Booking.Status.STUFFING,
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
    container = Container.objects.create(
        booking=booking,
        container_type=master_data['container_type'],
        container_size='20FT',
        container_count=1,
        container_no='MSKU1234567',
        stuffing_status='PENDING',
    )
    return booking, container


@pytest.fixture
def stock_items(db):
    """Create stock items with available inventory."""
    widget_a = StockItem.objects.create(product_name='Widget A', available_stock=100)
    widget_b = StockItem.objects.create(product_name='Widget B', available_stock=50)
    return {'Widget A': widget_a, 'Widget B': widget_b}


@pytest.mark.django_db
class TestStuffingAction:
    """Tests for the perform_stuffing service."""

    def test_successful_stuffing_deducts_stock(self, booking_with_container, stock_items, ops_user):
        """Stuffing deducts from available_stock and adds to shipped_stock."""
        _, container = booking_with_container
        product_quantities = [
            {'product_name': 'Widget A', 'quantity': 30},
            {'product_name': 'Widget B', 'quantity': 20},
        ]

        StockService.perform_stuffing(container.pk, product_quantities, ops_user)

        stock_items['Widget A'].refresh_from_db()
        stock_items['Widget B'].refresh_from_db()
        assert stock_items['Widget A'].available_stock == 70
        assert stock_items['Widget A'].shipped_stock == 30
        assert stock_items['Widget B'].available_stock == 30
        assert stock_items['Widget B'].shipped_stock == 20

    def test_stuffing_updates_container_status(self, booking_with_container, stock_items, ops_user):
        """Container is marked STUFFED with timestamp and user."""
        _, container = booking_with_container
        product_quantities = [{'product_name': 'Widget A', 'quantity': 10}]

        StockService.perform_stuffing(container.pk, product_quantities, ops_user)

        container.refresh_from_db()
        assert container.stuffing_status == 'STUFFED'
        assert container.stuffed_at is not None
        assert container.stuffed_by == ops_user

    def test_insufficient_stock_rejected(self, booking_with_container, stock_items, ops_user):
        """Stuffing is rejected if available stock is insufficient."""
        _, container = booking_with_container
        product_quantities = [{'product_name': 'Widget A', 'quantity': 200}]  # only 100 available

        with pytest.raises(ValidationError) as exc_info:
            StockService.perform_stuffing(container.pk, product_quantities, ops_user)
        assert 'Insufficient stock' in str(exc_info.value.detail['detail'])

    def test_atomicity_no_partial_deduction(self, booking_with_container, stock_items, ops_user):
        """If one product has insufficient stock, no stock changes occur (atomic)."""
        _, container = booking_with_container
        product_quantities = [
            {'product_name': 'Widget A', 'quantity': 30},  # Valid
            {'product_name': 'Widget B', 'quantity': 100},  # Exceeds available (50)
        ]

        with pytest.raises(ValidationError):
            StockService.perform_stuffing(container.pk, product_quantities, ops_user)

        # Widget A should NOT have been deducted
        stock_items['Widget A'].refresh_from_db()
        assert stock_items['Widget A'].available_stock == 100
        assert stock_items['Widget A'].shipped_stock == 0

    def test_duplicate_stuffing_rejected(self, booking_with_container, stock_items, ops_user):
        """Cannot stuff an already-stuffed container."""
        _, container = booking_with_container
        product_quantities = [{'product_name': 'Widget A', 'quantity': 10}]

        # First stuffing succeeds
        StockService.perform_stuffing(container.pk, product_quantities, ops_user)

        # Second stuffing is rejected
        with pytest.raises(ValidationError) as exc_info:
            StockService.perform_stuffing(container.pk, product_quantities, ops_user)
        assert 'already stuffed' in str(exc_info.value.detail['detail']).lower()

    def test_nonexistent_product_rejected(self, booking_with_container, ops_user):
        """Stuffing with a non-existent product raises ValidationError."""
        _, container = booking_with_container
        product_quantities = [{'product_name': 'Nonexistent', 'quantity': 10}]

        with pytest.raises(ValidationError) as exc_info:
            StockService.perform_stuffing(container.pk, product_quantities, ops_user)
        assert 'does not exist' in str(exc_info.value.detail['detail'])
