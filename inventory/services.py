"""
Business logic service layer for Inventory/Stock operations.
"""

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from bookings.models import Container
from inventory.models import StockItem


class StockService:
    """Service class for stock management operations."""

    @staticmethod
    @transaction.atomic
    def perform_stuffing(container_id, product_quantities, user):
        """
        Mark a container as stuffed and deduct stock atomically.

        Args:
            container_id: ID of the container to stuff.
            product_quantities: List of dicts with 'product_name' and 'quantity'.
            user: The authenticated user performing the action.

        Returns:
            The updated Container instance.

        Raises:
            ValidationError if container is already stuffed or insufficient stock.
        """
        container = Container.objects.select_for_update().get(pk=container_id)

        if container.stuffing_status == 'STUFFED':
            raise ValidationError(
                {'detail': 'Container is already stuffed.'}
            )

        # Validate and deduct stock for each product
        for item in product_quantities:
            product_name = item['product_name']
            quantity = item['quantity']

            try:
                stock = StockItem.objects.select_for_update().get(
                    product_name__iexact=product_name
                )
            except StockItem.DoesNotExist:
                raise ValidationError(
                    {'detail': f"Stock item '{product_name}' does not exist."}
                )

            if stock.available_stock < quantity:
                raise ValidationError(
                    {
                        'detail': (
                            f"Insufficient stock for '{product_name}': "
                            f"available={stock.available_stock}, requested={quantity}"
                        )
                    }
                )

            stock.available_stock -= quantity
            stock.shipped_stock += quantity
            stock.save()

        # Update container status
        container.stuffing_status = 'STUFFED'
        container.stuffed_at = timezone.now()
        container.stuffed_by = user
        container.save()

        return container
