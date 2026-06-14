"""
Django-filter FilterSet for booking search.
Supports structured filters, quick search, and combined AND logic.
"""

import django_filters
from django.db.models import Q

from bookings.models import Booking


class BookingFilterSet(django_filters.FilterSet):
    """
    FilterSet providing:
    - Structured filters: client, status, date ranges, consignee, shipping_line, etc.
    - Quick search (q): exact match across job_number, hbl_no, mbl_no,
      booking_no, quotation_no, shipper_invoice_no.
    - Container number search: exact match on related Container.container_no.
    All filters combine with AND logic.
    """

    # Structured filters
    client = django_filters.NumberFilter(field_name='client_id')
    consignee = django_filters.NumberFilter(field_name='consignee_id')
    shipping_line = django_filters.NumberFilter(field_name='shipping_line_id')
    sales_person = django_filters.NumberFilter(field_name='marketing_person_id')
    status = django_filters.ChoiceFilter(choices=Booking.Status.choices)
    vessel_voyage = django_filters.CharFilter(field_name='voyage', lookup_expr='icontains')
    handling_type = django_filters.CharFilter(field_name='shipment_type', lookup_expr='icontains')

    # Date range filters
    booking_date_from = django_filters.DateFilter(
        field_name='booking_date', lookup_expr='gte'
    )
    booking_date_to = django_filters.DateFilter(
        field_name='booking_date', lookup_expr='lte'
    )
    etd_from = django_filters.DateTimeFilter(
        field_name='etd_pol', lookup_expr='gte'
    )
    etd_to = django_filters.DateTimeFilter(
        field_name='etd_pol', lookup_expr='lte'
    )
    eta_from = django_filters.DateTimeFilter(
        field_name='eta_destination', lookup_expr='gte'
    )
    eta_to = django_filters.DateTimeFilter(
        field_name='eta_destination', lookup_expr='lte'
    )

    # Quick search: exact match across multiple reference fields
    q = django_filters.CharFilter(method='filter_quick_search')

    # Container number: exact match via related Container table
    container_no = django_filters.CharFilter(method='filter_container_no')

    class Meta:
        model = Booking
        fields = []

    def filter_quick_search(self, queryset, name, value):
        """
        Quick search: exact match on job_number, hbl_no, mbl_no,
        booking_no, quotation_no, or shipper_invoice_no.
        """
        if not value:
            return queryset
        return queryset.filter(
            Q(job_number=value)
            | Q(hbl_no=value)
            | Q(mbl_no=value)
            | Q(booking_no=value)
            | Q(quotation_no=value)
            | Q(shipper_invoice_no=value)
        )

    def filter_container_no(self, queryset, name, value):
        """Exact match on related Container.container_no."""
        if not value:
            return queryset
        return queryset.filter(containers__container_no=value).distinct()
