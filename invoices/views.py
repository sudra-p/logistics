"""
Views for Commercial Invoice and Packing List endpoints.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAccountsUser, IsAdminUser, IsOperationsUser

from .models import CommercialInvoice, PackingList
from .serializers import (
    CommercialInvoiceCreateSerializer,
    CommercialInvoiceDetailSerializer,
    CommercialInvoiceUpdateSerializer,
    PackingListCreateSerializer,
    PackingListDetailSerializer,
    PackingListUpdateSerializer,
)
from .services import CommercialInvoiceService, PackingListService


class CommercialInvoiceViewSet(viewsets.ViewSet):
    """
    ViewSet for Commercial Invoices.

    POST /api/bookings/{booking_id}/commercial-invoice/ — create
    GET /api/bookings/{booking_id}/commercial-invoice/ — list for booking
    GET /api/commercial-invoices/{id}/ — retrieve
    PATCH /api/commercial-invoices/{id}/ — update
    PATCH /api/commercial-invoices/{id}/finalize/ — finalize
    POST /api/commercial-invoices/{id}/revise/ — create revision
    """

    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'finalize', 'revise'):
            return [
                IsAuthenticated(),
                IsAccountsUser() | IsOperationsUser() | IsAdminUser(),
            ]
        return [IsAuthenticated()]


class BookingCommercialInvoiceView(viewsets.ViewSet):
    """
    POST /api/bookings/{id}/commercial-invoice/ — create
    GET /api/bookings/{id}/commercial-invoice/ — list for booking
    """

    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action == 'create':
            return [
                IsAuthenticated(),
                IsAccountsUser() | IsOperationsUser() | IsAdminUser(),
            ]
        return [IsAuthenticated()]

    def create(self, request, booking_id=None):
        """Create a Commercial Invoice for the given booking."""
        serializer = CommercialInvoiceCreateSerializer(data={
            'booking_id': booking_id,
            **request.data,
        })
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        invoice = CommercialInvoiceService.create_commercial_invoice(
            booking_id=data['booking_id'],
            user=request.user,
            line_items=data.get('line_items'),
        )

        response_serializer = CommercialInvoiceDetailSerializer(invoice)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, booking_id=None):
        """List Commercial Invoices for a booking."""
        invoices = CommercialInvoice.objects.filter(
            booking_id=booking_id
        ).select_related('booking', 'created_by').prefetch_related('line_items')

        serializer = CommercialInvoiceDetailSerializer(invoices, many=True)
        return Response(serializer.data)


class CommercialInvoiceDetailView(viewsets.ViewSet):
    """
    GET /api/commercial-invoices/{id}/ — retrieve
    PATCH /api/commercial-invoices/{id}/ — update
    PATCH /api/commercial-invoices/{id}/finalize/ — finalize
    POST /api/commercial-invoices/{id}/revise/ — create revision
    """

    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ('partial_update', 'finalize', 'revise'):
            return [
                IsAuthenticated(),
                IsAccountsUser() | IsOperationsUser() | IsAdminUser(),
            ]
        return [IsAuthenticated()]

    def retrieve(self, request, pk=None):
        """Get a Commercial Invoice by ID."""
        try:
            invoice = CommercialInvoice.objects.select_related(
                'booking', 'created_by'
            ).prefetch_related('line_items').get(pk=pk)
        except CommercialInvoice.DoesNotExist:
            return Response(
                {'detail': 'Not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CommercialInvoiceDetailSerializer(invoice)
        return Response(serializer.data)

    def partial_update(self, request, pk=None):
        """Update a Commercial Invoice."""
        serializer = CommercialInvoiceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        invoice = CommercialInvoiceService.update_invoice(
            invoice_id=pk,
            user=request.user,
            line_items=serializer.validated_data.get('line_items'),
        )

        response_serializer = CommercialInvoiceDetailSerializer(invoice)
        return Response(response_serializer.data)

    @action(detail=True, methods=['patch'], url_path='finalize')
    def finalize(self, request, pk=None):
        """Finalize a Commercial Invoice."""
        invoice = CommercialInvoiceService.finalize_invoice(
            invoice_id=pk,
            user=request.user,
        )
        serializer = CommercialInvoiceDetailSerializer(invoice)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='revise')
    def revise(self, request, pk=None):
        """Create a new revision of a finalized Invoice."""
        invoice = CommercialInvoiceService.create_revision(
            invoice_id=pk,
            user=request.user,
        )
        serializer = CommercialInvoiceDetailSerializer(invoice)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BookingPackingListView(viewsets.ViewSet):
    """
    POST /api/bookings/{id}/packing-list/ — create
    GET /api/bookings/{id}/packing-list/ — list for booking
    """

    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action == 'create':
            return [
                IsAuthenticated(),
                IsAccountsUser() | IsOperationsUser() | IsAdminUser(),
            ]
        return [IsAuthenticated()]

    def create(self, request, booking_id=None):
        """Create a Packing List for the given booking."""
        serializer = PackingListCreateSerializer(data={
            'booking_id': booking_id,
            **request.data,
        })
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        packing_list = PackingListService.create_packing_list(
            booking_id=data['booking_id'],
            user=request.user,
            line_items=data.get('line_items'),
        )

        response_serializer = PackingListDetailSerializer(packing_list)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, booking_id=None):
        """List Packing Lists for a booking."""
        packing_lists = PackingList.objects.filter(
            booking_id=booking_id
        ).select_related('booking', 'created_by').prefetch_related('line_items')

        serializer = PackingListDetailSerializer(packing_lists, many=True)
        return Response(serializer.data)


class PackingListDetailView(viewsets.ViewSet):
    """
    GET /api/packing-lists/{id}/ — retrieve
    PATCH /api/packing-lists/{id}/ — update
    PATCH /api/packing-lists/{id}/finalize/ — finalize
    POST /api/packing-lists/{id}/revise/ — create revision
    """

    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ('partial_update', 'finalize', 'revise'):
            return [
                IsAuthenticated(),
                IsAccountsUser() | IsOperationsUser() | IsAdminUser(),
            ]
        return [IsAuthenticated()]

    def retrieve(self, request, pk=None):
        """Get a Packing List by ID."""
        try:
            packing_list = PackingList.objects.select_related(
                'booking', 'created_by'
            ).prefetch_related('line_items').get(pk=pk)
        except PackingList.DoesNotExist:
            return Response(
                {'detail': 'Not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PackingListDetailSerializer(packing_list)
        return Response(serializer.data)

    def partial_update(self, request, pk=None):
        """Update a Packing List."""
        serializer = PackingListUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        packing_list = PackingListService.update_packing_list(
            packing_list_id=pk,
            user=request.user,
            line_items=serializer.validated_data.get('line_items'),
        )

        response_serializer = PackingListDetailSerializer(packing_list)
        return Response(response_serializer.data)

    @action(detail=True, methods=['patch'], url_path='finalize')
    def finalize(self, request, pk=None):
        """Finalize a Packing List."""
        packing_list = PackingListService.finalize_packing_list(
            packing_list_id=pk,
            user=request.user,
        )
        serializer = PackingListDetailSerializer(packing_list)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='revise')
    def revise(self, request, pk=None):
        """Create a new revision of a finalized Packing List."""
        packing_list = PackingListService.create_revision(
            packing_list_id=pk,
            user=request.user,
        )
        serializer = PackingListDetailSerializer(packing_list)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
