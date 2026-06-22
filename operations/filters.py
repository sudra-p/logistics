"""
Filters for the Operations Tracking View.
"""

import django_filters

from bookings.models import Booking


class OperationsTrackingFilterSet(django_filters.FilterSet):
    """
    FilterSet for the Operations Tracking view.

    Supports filtering by:
    - customer: Client FK (by ID)
    - shipping_line: ShippingLine FK (by ID)
    - status: Booking status (choice)
    - etd_from / etd_to: ETD date range on etd_pol field
    - pol: Port of Loading FK (by ID)
    """

    customer = django_filters.NumberFilter(field_name='client_id')
    shipping_line = django_filters.NumberFilter(field_name='shipping_line_id')
    status = django_filters.ChoiceFilter(choices=Booking.Status.choices)
    etd_from = django_filters.DateTimeFilter(
        field_name='etd_pol', lookup_expr='gte'
    )
    etd_to = django_filters.DateTimeFilter(
        field_name='etd_pol', lookup_expr='lte'
    )
    pol = django_filters.NumberFilter(field_name='pol_id')

    class Meta:
        model = Booking
        fields = ['customer', 'shipping_line', 'status', 'etd_from', 'etd_to', 'pol']
