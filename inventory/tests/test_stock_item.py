"""
Tests for StockItem CRUD and constraints.
Task 25.5: Test non-negative values.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import IntegrityError
from rest_framework import status
from rest_framework.test import APIClient

from inventory.models import StockItem

User = get_user_model()


@pytest.fixture
def ops_user(db):
    user = User.objects.create_user(username='ops_user', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Operations')
    user.groups.add(group)
    return user


@pytest.fixture
def ops_client(ops_user):
    client = APIClient()
    client.force_authenticate(user=ops_user)
    return client


@pytest.mark.django_db
class TestStockItemCRUD:
    """Tests for StockItem model CRUD operations."""

    def test_create_stock_item(self):
        """Can create a stock item with valid data."""
        item = StockItem.objects.create(
            product_name='Widget A',
            available_stock=100,
            unit='pcs',
        )
        assert item.pk is not None
        assert item.available_stock == 100
        assert item.reserved_stock == 0
        assert item.shipped_stock == 0

    def test_default_reserved_and_shipped_are_zero(self):
        """Reserved and shipped default to 0 on creation."""
        item = StockItem.objects.create(product_name='Widget B', available_stock=50)
        assert item.reserved_stock == 0
        assert item.shipped_stock == 0

    def test_unique_product_name_constraint(self):
        """Cannot create two stock items with the same product name."""
        StockItem.objects.create(product_name='Widget A', available_stock=100)
        with pytest.raises(IntegrityError):
            StockItem.objects.create(product_name='Widget A', available_stock=50)

    def test_update_stock_item(self):
        """Can update stock item quantities."""
        item = StockItem.objects.create(product_name='Widget A', available_stock=100)
        item.available_stock = 80
        item.shipped_stock = 20
        item.save()
        item.refresh_from_db()
        assert item.available_stock == 80
        assert item.shipped_stock == 20

    def test_delete_stock_item(self):
        """Can delete a stock item."""
        item = StockItem.objects.create(product_name='Widget A', available_stock=100)
        pk = item.pk
        item.delete()
        assert not StockItem.objects.filter(pk=pk).exists()


@pytest.mark.django_db
class TestStockItemConstraints:
    """Tests for non-negative stock constraints."""

    def test_negative_available_stock_rejected(self):
        """Available stock cannot be negative (DB constraint)."""
        item = StockItem.objects.create(product_name='Widget A', available_stock=10)
        item.available_stock = -1
        with pytest.raises(IntegrityError):
            item.save()

    def test_negative_reserved_stock_rejected(self):
        """Reserved stock cannot be negative (DB constraint)."""
        item = StockItem.objects.create(product_name='Widget B', available_stock=10)
        item.reserved_stock = -1
        with pytest.raises(IntegrityError):
            item.save()

    def test_negative_shipped_stock_rejected(self):
        """Shipped stock cannot be negative (DB constraint)."""
        item = StockItem.objects.create(product_name='Widget C', available_stock=10)
        item.shipped_stock = -1
        with pytest.raises(IntegrityError):
            item.save()

    def test_zero_values_allowed(self):
        """Zero values are valid for all stock fields."""
        item = StockItem.objects.create(
            product_name='Widget D',
            available_stock=0,
            reserved_stock=0,
            shipped_stock=0,
        )
        assert item.pk is not None
