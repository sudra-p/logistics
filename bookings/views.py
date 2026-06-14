"""
ViewSet for Booking CRUD operations, transhipment and container management.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import CanModifyBooking, CanViewBooking
from bookings.models import Booking, TranshipmentLeg
from bookings.serializers import (
    BookingCreateSerializer,
    BookingDetailSerializer,
    BookingStatusHistorySerializer,
    BookingUpdateSerializer,
    ContainerDetailSerializer,
    ContainerSerializer,
    StatusChangeSerializer,
    TranshipmentLegDetailSerializer,
    TranshipmentLegSerializer,
    TranshipmentLegsCreateSerializer,
)
from bookings.services import BookingService


class BookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing bookings.

    - POST /api/bookings/ — create (CanModifyBooking: Ops or Admin)
    - GET /api/bookings/ — list (CanViewBooking)
    - GET /api/bookings/{id}/ — retrieve (CanViewBooking)
    """

    queryset = Booking.objects.all()

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy', 'change_status'):
            return [CanModifyBooking()]
        return [CanViewBooking()]

    def get_queryset(self):
        """
        Sales users only see bookings where they are the marketing person.
        All other roles see all bookings.
        """
        qs = Booking.objects.all()
        user = self.request.user

        if user.is_authenticated and user.groups.filter(name='Sales').exists():
            # Sales users only see their own bookings
            qs = qs.filter(marketing_person__user=user)

        return qs

    def get_serializer_class(self):
        if self.action == 'create':
            return BookingCreateSerializer
        if self.action in ('update', 'partial_update'):
            return BookingUpdateSerializer
        return BookingDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        booking = BookingService.create_booking(
            data=serializer.validated_data,
            user=request.user,
        )

        response_serializer = BookingDetailSerializer(booking)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        booking = self.get_object()
        serializer = BookingUpdateSerializer(
            data=request.data,
            booking_instance=booking,
        )
        serializer.is_valid(raise_exception=True)

        updated_booking = BookingService.update_booking(
            booking_id=booking.pk,
            data=serializer.validated_data,
            user=request.user,
        )

        response_serializer = BookingDetailSerializer(updated_booking)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        booking = self.get_object()
        serializer = BookingUpdateSerializer(
            data=request.data,
            booking_instance=booking,
        )
        serializer.is_valid(raise_exception=True)

        updated_booking = BookingService.update_booking(
            booking_id=booking.pk,
            data=serializer.validated_data,
            user=request.user,
        )

        response_serializer = BookingDetailSerializer(updated_booking)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], url_path='status')
    def change_status(self, request, pk=None):
        """PATCH /api/bookings/{id}/status/ — Change booking status."""
        serializer = StatusChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        booking = BookingService.change_status(
            booking_id=pk,
            new_status=serializer.validated_data['status'],
            user=request.user,
        )

        response_serializer = BookingDetailSerializer(booking)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='history')
    def history(self, request, pk=None):
        """GET /api/bookings/{id}/history/ — Get status history for a booking."""
        booking = self.get_object()
        history = booking.status_history.all()
        serializer = BookingStatusHistorySerializer(history, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TranshipmentListCreateView(APIView):
    """
    POST /api/bookings/{id}/transhipments/ — Add transhipment legs to a booking.
    GET /api/bookings/{id}/transhipments/ — List transhipment legs for a booking.
    """

    permission_classes = [CanModifyBooking]

    def get_permissions(self):
        if self.request.method == 'GET':
            return [CanViewBooking()]
        return [CanModifyBooking()]

    def get(self, request, booking_id):
        legs = TranshipmentLeg.objects.filter(booking_id=booking_id).order_by('sequence')
        serializer = TranshipmentLegDetailSerializer(legs, many=True)
        return Response(serializer.data)

    def post(self, request, booking_id):
        serializer = TranshipmentLegsCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        created_legs = BookingService.add_transhipments(
            booking_id=booking_id,
            legs_data=serializer.validated_data['legs'],
            user=request.user,
        )

        response_serializer = TranshipmentLegDetailSerializer(created_legs, many=True)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class TranshipmentDetailView(APIView):
    """
    PUT /api/bookings/{id}/transhipments/{tid}/ — Update a transhipment leg.
    DELETE /api/bookings/{id}/transhipments/{tid}/ — Remove a transhipment leg.
    """

    permission_classes = [CanModifyBooking]

    def put(self, request, booking_id, leg_id):
        serializer = TranshipmentLegSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_leg = BookingService.update_transhipment(
            booking_id=booking_id,
            leg_id=leg_id,
            data=serializer.validated_data,
            user=request.user,
        )

        response_serializer = TranshipmentLegDetailSerializer(updated_leg)
        return Response(response_serializer.data)

    def delete(self, request, booking_id, leg_id):
        BookingService.remove_transhipment(
            booking_id=booking_id,
            leg_id=leg_id,
            user=request.user,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class ContainerListCreateView(APIView):
    """
    POST /api/bookings/{id}/containers/ — Add containers to a booking.
    GET /api/bookings/{id}/containers/ — List containers for a booking.
    """

    def get_permissions(self):
        if self.request.method == 'GET':
            return [CanViewBooking()]
        return [CanModifyBooking()]

    def get(self, request, booking_id):
        from bookings.models import Container

        containers = Container.objects.filter(booking_id=booking_id)
        serializer = ContainerDetailSerializer(containers, many=True)
        return Response(serializer.data)

    def post(self, request, booking_id):
        # Accept both a single object and a list of objects
        data = request.data
        if isinstance(data, dict):
            data = [data]

        serializer = ContainerSerializer(data=data, many=True)
        serializer.is_valid(raise_exception=True)

        created_containers = BookingService.add_containers(
            booking_id=booking_id,
            containers_data=serializer.validated_data,
            user=request.user,
        )

        response_serializer = ContainerDetailSerializer(created_containers, many=True)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ContainerDetailView(APIView):
    """
    DELETE /api/bookings/{id}/containers/{cid}/ — Remove a container.
    """

    permission_classes = [CanModifyBooking]

    def delete(self, request, booking_id, container_id):
        BookingService.remove_container(
            booking_id=booking_id,
            container_id=container_id,
            user=request.user,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
