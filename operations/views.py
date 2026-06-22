"""
Views for the Operations Tracking View.
"""

from django.db.models import Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import CanManageInventory
from bookings.models import Booking, Container
from logistics.pagination import StandardPagination

from .filters import OperationsTrackingFilterSet
from .serializers import OperationsTrackingSerializer


class OperationsTrackingOrderingFilter(OrderingFilter):
    """
    Custom ordering filter that maps API field names to model field paths.
    Allows clients to sort using display field names (e.g., ?ordering=etd)
    which are translated to actual model lookups (e.g., etd_pol).
    """

    FIELD_MAP = {
        'pi_number': 'proforma_invoice__pi_number',
        'booking_number': 'job_number',
        'consignee': 'consignee__name',
        'shipping_line': 'shipping_line__name',
        'vessel_name': 'vessel__name',
        'voyage': 'voyage',
        'pol': 'pol__name',
        'pod': 'pod__name',
        'fpd': 'fpd__name',
        'etd': 'etd_pol',
        'eta': 'eta_destination',
        'forwarder': 'nvocc_forwarder__name',
    }

    def get_ordering(self, request, queryset, view):
        params = request.query_params.get(self.ordering_param)
        if params:
            fields = [param.strip() for param in params.split(',')]
            valid_fields = list(self.FIELD_MAP.keys())
            ordering = []
            for field in fields:
                descending = field.startswith('-')
                field_name = field.lstrip('-')
                if field_name in valid_fields:
                    db_field = self.FIELD_MAP[field_name]
                    ordering.append(f'-{db_field}' if descending else db_field)
            if ordering:
                return ordering
        return self.get_default_ordering(view)


class OperationsTrackingView(ListAPIView):
    """
    GET /api/operations/
    Returns a paginated list of all bookings for operations tracking.
    Accessible to Operations and Admin users only.
    """

    serializer_class = OperationsTrackingSerializer
    permission_classes = [IsAuthenticated, CanManageInventory]
    pagination_class = StandardPagination
    filterset_class = OperationsTrackingFilterSet
    filter_backends = [DjangoFilterBackend, SearchFilter, OperationsTrackingOrderingFilter]
    ordering = ['-booking_date']

    def get_queryset(self):
        return (
            Booking.objects.all()
            .select_related(
                'client',
                'shipping_line',
                'vessel',
                'pol',
                'pod',
                'fpd',
                'consignee',
                'nvocc_forwarder',
                'proforma_invoice',
            )
            .prefetch_related(
                Prefetch(
                    'containers',
                    queryset=Container.objects.select_related('container_type'),
                )
            )
        )
