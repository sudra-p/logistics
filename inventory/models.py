from django.db import models


UNIT_CHOICES = [
    ('units', 'Units'),
    ('kg', 'Kilograms (kg)'),
    ('bags', 'Bags'),
    ('tonnes', 'Tonnes'),
    ('litres', 'Litres'),
    ('meters', 'Meters'),
    ('pieces', 'Pieces'),
    ('boxes', 'Boxes'),
    ('cartons', 'Cartons'),
    ('pallets', 'Pallets'),
]


class StockItem(models.Model):
    """Inventory stock item for tracking available, reserved, and shipped quantities."""

    product_name = models.CharField(max_length=255, unique=True)
    available_stock = models.PositiveIntegerField(default=0)
    reserved_stock = models.PositiveIntegerField(default=0)
    shipped_stock = models.PositiveIntegerField(default=0)
    unit = models.CharField(max_length=50, default='units', choices=UNIT_CHOICES)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(available_stock__gte=0),
                name='available_stock_non_negative',
            ),
            models.CheckConstraint(
                condition=models.Q(reserved_stock__gte=0),
                name='reserved_stock_non_negative',
            ),
            models.CheckConstraint(
                condition=models.Q(shipped_stock__gte=0),
                name='shipped_stock_non_negative',
            ),
        ]

    def __str__(self):
        return f"{self.product_name} (available: {self.available_stock})"
