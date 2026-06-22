"""
Views for Inventory/Stock management.
"""

from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminUser, IsOperationsUser
from bookings.models import Container
from bookings.serializers import ContainerDetailSerializer
from inventory.models import StockItem
from inventory.serializers import StockItemSerializer, StuffingActionSerializer
from inventory.services import StockService


class StockItemViewSet(viewsets.ModelViewSet):
    """CRUD ViewSet for StockItem - accessible by Operations and Admin users."""

    queryset = StockItem.objects.all()
    serializer_class = StockItemSerializer
    permission_classes = [IsAuthenticated, (IsOperationsUser | IsAdminUser)]

    def get_permissions(self):
        return [IsAuthenticated(), IsOperationsUser() | IsAdminUser()]


class StuffingView(APIView):
    """
    POST endpoint to mark a container as stuffed with stock deductions.
    URL: /api/bookings/{booking_id}/containers/{container_id}/stuff/
    """

    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        return [IsAuthenticated(), IsOperationsUser() | IsAdminUser()]

    def post(self, request, booking_id, container_id):
        """Perform stuffing action on a container."""
        # Validate the container belongs to the booking
        try:
            container = Container.objects.get(
                pk=container_id, booking_id=booking_id
            )
        except Container.DoesNotExist:
            return Response(
                {'detail': 'Container not found for this booking.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = StuffingActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_container = StockService.perform_stuffing(
            container_id=container_id,
            product_quantities=serializer.validated_data['product_quantities'],
            user=request.user,
        )

        response_serializer = ContainerDetailSerializer(updated_container)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
