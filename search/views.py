"""
Search endpoint for bookings with filtering, pagination, and sorting.
"""

from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from accounts.permissions import CanViewBooking
from bookings.models import Booking
from bookings.serializers import BookingDetailSerializer
from logistics.pagination import StandardPagination
from search.filters import BookingFilterSet


class BookingSearchView(ListAPIView):
    """
    GET /api/bookings/search/

    Search and filter bookings with:
    - Structured filters (client, status, date ranges, etc.)
    - Quick search (q) for exact match on reference numbers
    - Container number search
    - Pagination (default 25, max 100)
    - Sorting (default: booking_date descending)

    All filters combine with AND logic.
    """

    queryset = Booking.objects.select_related(
        'client', 'shipping_line', 'pol', 'pod'
    ).all()
    serializer_class = BookingDetailSerializer
    filterset_class = BookingFilterSet
    pagination_class = StandardPagination
    permission_classes = [CanViewBooking]
    ordering = ['-booking_date']
    ordering_fields = [
        'booking_date', 'job_number', 'status',
        'etd_pol', 'eta_destination', 'created_at',
    ]

    def list(self, request, *args, **kwargs):
        """Override list to validate date range inputs before filtering."""
        validation_error = self._validate_date_ranges(request.query_params)
        if validation_error:
            return Response(
                {'detail': validation_error},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().list(request, *args, **kwargs)

    def _validate_date_ranges(self, params):
        """
        Validate that 'from' dates are not after 'to' dates.
        Returns error message string or None if valid.
        """
        date_range_pairs = [
            ('booking_date_from', 'booking_date_to', 'Booking date'),
            ('etd_from', 'etd_to', 'ETD'),
            ('eta_from', 'eta_to', 'ETA'),
        ]

        for from_key, to_key, label in date_range_pairs:
            from_val = params.get(from_key)
            to_val = params.get(to_key)
            if from_val and to_val and from_val > to_val:
                return f'{label} range is invalid: {from_key} must not be after {to_key}.'

        return None
