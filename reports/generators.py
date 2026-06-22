from datetime import timedelta

from django.db.models import Q, Sum
from django.utils import timezone

from bookings.models import Booking


class ReportGenerator:
    """Generates report querysets for sea export forwarding operations."""

    @staticmethod
    def pending_do_report(filters=None):
        """
        Generate the Pending DO report queryset.

        Filters bookings with status 'PENDING' or 'DO_BOOKING_EDIT'.
        Supports filtering by client, vessel/voyage, booking date range, and shipping line.
        Defaults to last 30 days if no date range specified.

        Args:
            filters: dict with optional keys:
                - client: client ID
                - vessel_voyage: vessel/voyage search string (icontains)
                - booking_date_from: start date (inclusive)
                - booking_date_to: end date (inclusive)
                - shipping_line: shipping line ID

        Returns:
            QuerySet of Booking objects annotated with container_count.
        """
        if filters is None:
            filters = {}

        queryset = Booking.objects.filter(
            status__in=[Booking.Status.PENDING, Booking.Status.BOOKED]
        )

        # Apply client filter
        client = filters.get('client')
        if client:
            queryset = queryset.filter(client_id=client)

        # Apply vessel/voyage filter (search in vessel name and voyage field)
        vessel_voyage = filters.get('vessel_voyage')
        if vessel_voyage:
            queryset = queryset.filter(
                Q(vessel__name__icontains=vessel_voyage)
                | Q(voyage__icontains=vessel_voyage)
            )

        # Apply shipping line filter
        shipping_line = filters.get('shipping_line')
        if shipping_line:
            queryset = queryset.filter(shipping_line_id=shipping_line)

        # Apply date range filter (default to last 30 days)
        booking_date_from = filters.get('booking_date_from')
        booking_date_to = filters.get('booking_date_to')

        if not booking_date_from and not booking_date_to:
            # Default to last 30 days
            booking_date_from = timezone.now().date() - timedelta(days=30)
            booking_date_to = timezone.now().date()

        if booking_date_from:
            queryset = queryset.filter(booking_date__gte=booking_date_from)
        if booking_date_to:
            queryset = queryset.filter(booking_date__lte=booking_date_to)

        # Annotate with container count (sum of container_count field on Container model)
        queryset = queryset.annotate(
            total_container_count=Sum('containers__container_count')
        )

        # Select related for performance
        queryset = queryset.select_related(
            'client', 'shipping_line', 'pol', 'pod', 'vessel'
        )

        # Order by booking_date ascending
        queryset = queryset.order_by('booking_date')

        return queryset

    @staticmethod
    def master_report(filters=None):
        """
        Generate the Master report queryset.

        Includes all bookings regardless of status.
        Supports filtering by client, vessel/voyage, created date range, status,
        and shipping line.
        Defaults to last 90 days (based on created_at) if no date range specified.

        Args:
            filters: dict with optional keys:
                - client: client ID
                - vessel_voyage: vessel/voyage search string (icontains)
                - created_date_from: start date (inclusive, on created_at)
                - created_date_to: end date (inclusive, on created_at)
                - status: booking status value
                - shipping_line: shipping line ID

        Returns:
            QuerySet of Booking objects annotated with container_count,
            sorted by created_at descending.
        """
        if filters is None:
            filters = {}

        queryset = Booking.objects.all()

        # Apply client filter
        client = filters.get('client')
        if client:
            queryset = queryset.filter(client_id=client)

        # Apply vessel/voyage filter (search in vessel name and voyage field)
        vessel_voyage = filters.get('vessel_voyage')
        if vessel_voyage:
            queryset = queryset.filter(
                Q(vessel__name__icontains=vessel_voyage)
                | Q(voyage__icontains=vessel_voyage)
            )

        # Apply shipping line filter
        shipping_line = filters.get('shipping_line')
        if shipping_line:
            queryset = queryset.filter(shipping_line_id=shipping_line)

        # Apply status filter
        status = filters.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # Apply date range filter on created_at (default to last 90 days)
        created_date_from = filters.get('created_date_from')
        created_date_to = filters.get('created_date_to')

        if not created_date_from and not created_date_to:
            # Default to last 90 days
            created_date_from = timezone.now().date() - timedelta(days=90)
            created_date_to = timezone.now().date()

        if created_date_from:
            queryset = queryset.filter(created_at__date__gte=created_date_from)
        if created_date_to:
            queryset = queryset.filter(created_at__date__lte=created_date_to)

        # Annotate with container count
        queryset = queryset.annotate(
            total_container_count=Sum('containers__container_count')
        )

        # Select related for performance
        queryset = queryset.select_related(
            'client', 'shipping_line', 'pol', 'pod', 'vessel'
        )

        # Order by created_at descending
        queryset = queryset.order_by('-created_at')

        return queryset
