"""
Views for Bill of Lading endpoints.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import CanManageBL

from .models import BillOfLading
from .serializers import (
    BillOfLadingCreateSerializer,
    BillOfLadingDetailSerializer,
    BillOfLadingStatusSerializer,
    BillOfLadingUpdateSerializer,
)
from .services import BillOfLadingService


class BookingBLView(viewsets.ViewSet):
    """
    POST /api/bookings/{id}/bl/ — create BL
    GET /api/bookings/{id}/bl/ — list BLs for booking
    """

    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), CanManageBL()]
        return [IsAuthenticated()]

    def create(self, request, booking_id=None):
        """Create a Bill of Lading for the given booking."""
        serializer = BillOfLadingCreateSerializer(data={
            'booking_id': booking_id,
            **request.data,
        })
        serializer.is_valid(raise_exception=True)

        bl = BillOfLadingService.create_bl(
            booking_id=serializer.validated_data['booking_id'],
            user=request.user,
            data=serializer.validated_data,
        )

        response_serializer = BillOfLadingDetailSerializer(bl)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, booking_id=None):
        """List Bills of Lading for a booking."""
        bls = BillOfLading.objects.filter(
            booking_id=booking_id
        ).select_related('booking', 'shipper', 'consignee', 'created_by')

        serializer = BillOfLadingDetailSerializer(bls, many=True)
        return Response(serializer.data)


class BLDetailView(viewsets.ViewSet):
    """
    GET /api/bl/{id}/ — retrieve
    PATCH /api/bl/{id}/ — update
    PATCH /api/bl/{id}/status/ — change status
    """

    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ('partial_update', 'change_status'):
            return [IsAuthenticated(), CanManageBL()]
        return [IsAuthenticated()]

    def retrieve(self, request, pk=None):
        """Get a Bill of Lading by ID."""
        try:
            bl = BillOfLading.objects.select_related(
                'booking', 'shipper', 'consignee', 'created_by'
            ).get(pk=pk)
        except BillOfLading.DoesNotExist:
            return Response(
                {'detail': 'Not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = BillOfLadingDetailSerializer(bl)
        return Response(serializer.data)

    def partial_update(self, request, pk=None):
        """Update a Bill of Lading (only DRAFT)."""
        serializer = BillOfLadingUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        bl = BillOfLadingService.update_bl(
            bl_id=pk,
            user=request.user,
            data=serializer.validated_data,
        )

        response_serializer = BillOfLadingDetailSerializer(bl)
        return Response(response_serializer.data)

    @action(detail=True, methods=['patch'], url_path='status')
    def change_status(self, request, pk=None):
        """Change BL status (DRAFT → SUBMITTED → RELEASED)."""
        serializer = BillOfLadingStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        bl = BillOfLadingService.change_bl_status(
            bl_id=pk,
            new_status=serializer.validated_data['status'],
            user=request.user,
        )

        response_serializer = BillOfLadingDetailSerializer(bl)
        return Response(response_serializer.data)
