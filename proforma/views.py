"""
ViewSet for Proforma Invoice CRUD operations and status transitions.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import CanManageProforma, CanViewProforma
from proforma.models import ProformaInvoice
from proforma.serializers import (
    ProformaInvoiceCreateSerializer,
    ProformaInvoiceDetailSerializer,
    ProformaInvoiceUpdateSerializer,
)
from proforma.services import ProformaService
from payments.models import Payment
from payments.serializers import PaymentDetailSerializer


class ProformaInvoiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Proforma Invoices.

    - POST /api/proforma-invoices/ — create (Accounts, Admin)
    - GET /api/proforma-invoices/ — list (Accounts, Admin, Sales filtered)
    - GET /api/proforma-invoices/{id}/ — retrieve (Accounts, Admin, Sales filtered)
    - PATCH /api/proforma-invoices/{id}/ — update (Accounts, Admin)
    - PATCH /api/proforma-invoices/{id}/status/ — change status (Accounts, Admin)
    """

    queryset = ProformaInvoice.objects.all()

    def get_permissions(self):
        """
        Write operations: CanManageProforma (Accounts or Admin).
        Read operations: CanViewProforma (Accounts, Admin, or Sales).
        Superuser bypasses all group checks (handled inside permission classes).
        """
        if self.action in ('create', 'update', 'partial_update', 'destroy', 'change_status'):
            return [IsAuthenticated(), CanManageProforma()]
        # Read access: Accounts, Admin, or Sales
        return [IsAuthenticated(), CanViewProforma()]

    def get_queryset(self):
        """
        Sales users only see PIs where the customer is linked to their marketing_person.
        All other roles see all PIs.
        """
        qs = ProformaInvoice.objects.all()
        user = self.request.user

        if not user.is_authenticated:
            return qs.none()

        # Superuser, Admin, or Accounts see everything
        if user.is_superuser:
            return qs

        if user.groups.filter(name__in=['Admin', 'Accounts']).exists():
            return qs

        # Sales users: filter to PIs where customer has a marketing_person linked to this user
        if user.groups.filter(name='Sales').exists():
            from bookings.models import Booking
            # Find clients associated with this user via MarketingPerson
            from master_data.models import MarketingPerson
            marketing_persons = MarketingPerson.objects.filter(user=user)
            # Get bookings with this marketing person and extract client IDs
            client_ids = Booking.objects.filter(
                marketing_person__in=marketing_persons
            ).values_list('client_id', flat=True).distinct()
            qs = qs.filter(customer_id__in=client_ids)

        return qs

    def get_serializer_class(self):
        if self.action == 'create':
            return ProformaInvoiceCreateSerializer
        if self.action in ('update', 'partial_update'):
            return ProformaInvoiceUpdateSerializer
        return ProformaInvoiceDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pi = ProformaService.create_proforma(
            data=serializer.validated_data,
            user=request.user,
        )

        response_serializer = ProformaInvoiceDetailSerializer(pi)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        pi = self.get_object()
        serializer = ProformaInvoiceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_pi = ProformaService.update_proforma(
            pi_id=pi.pk,
            data=serializer.validated_data,
            user=request.user,
        )

        response_serializer = ProformaInvoiceDetailSerializer(updated_pi)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        pi = self.get_object()
        serializer = ProformaInvoiceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_pi = ProformaService.update_proforma(
            pi_id=pi.pk,
            data=serializer.validated_data,
            user=request.user,
        )

        response_serializer = ProformaInvoiceDetailSerializer(updated_pi)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], url_path='status')
    def change_status(self, request, pk=None):
        """PATCH /api/proforma-invoices/{id}/status/ — Change PI status."""
        new_status = request.data.get('status')
        if not new_status:
            return Response(
                {'status': 'This field is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate status is a valid choice
        valid_choices = [choice[0] for choice in ProformaInvoice.Status.choices]
        if new_status not in valid_choices:
            return Response(
                {'status': f'Invalid status. Must be one of: {valid_choices}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pi = ProformaService.change_status(
            pi_id=pk,
            new_status=new_status,
            user=request.user,
        )

        response_serializer = ProformaInvoiceDetailSerializer(pi)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='payments')
    def payments(self, request, pk=None):
        """GET /api/proforma-invoices/{id}/payments/ — List payments for this PI."""
        pi = self.get_object()
        payments_qs = Payment.objects.filter(
            proforma_invoice=pi
        ).select_related('proforma_invoice', 'proforma_invoice__customer', 'created_by')
        serializer = PaymentDetailSerializer(payments_qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
