"""
ViewSet for Payment CRUD operations.
"""

from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAccountsUser, IsAdminUser
from payments.models import Payment
from payments.serializers import PaymentCreateSerializer, PaymentDetailSerializer
from payments.services import PaymentService


class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Payments.

    - POST /api/payments/ — create (Accounts, Admin)
    - GET /api/payments/ — list (Accounts, Admin)
    - GET /api/payments/{id}/ — retrieve (Accounts, Admin)
    - GET /api/payments/?proforma_invoice={id} — filter by PI

    No update or delete operations are supported (payments are immutable records).
    """

    queryset = Payment.objects.select_related(
        'proforma_invoice', 'proforma_invoice__customer', 'created_by'
    ).all()
    http_method_names = ['get', 'post', 'head', 'options']

    def get_permissions(self):
        """Only Accounts or Admin users can access payments."""
        return [IsAuthenticated(), IsAccountsUser() | IsAdminUser()]

    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentCreateSerializer
        return PaymentDetailSerializer

    def get_queryset(self):
        """Support filtering by proforma_invoice query param."""
        qs = super().get_queryset()
        pi_id = self.request.query_params.get('proforma_invoice')
        if pi_id:
            qs = qs.filter(proforma_invoice_id=pi_id)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment = PaymentService.record_payment(
            data=serializer.validated_data,
            user=request.user,
        )

        response_serializer = PaymentDetailSerializer(payment)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
