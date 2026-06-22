from django.urls import path

from .views import (
    BookingCommercialInvoiceView,
    BookingPackingListView,
    CommercialInvoiceDetailView,
    PackingListDetailView,
)

app_name = 'invoices'

# Booking-scoped endpoints
booking_commercial_invoice_view = BookingCommercialInvoiceView.as_view({
    'get': 'list',
    'post': 'create',
})

booking_packing_list_view = BookingPackingListView.as_view({
    'get': 'list',
    'post': 'create',
})

# Detail endpoints
commercial_invoice_detail_view = CommercialInvoiceDetailView.as_view({
    'get': 'retrieve',
    'patch': 'partial_update',
})

commercial_invoice_finalize_view = CommercialInvoiceDetailView.as_view({
    'patch': 'finalize',
})

commercial_invoice_revise_view = CommercialInvoiceDetailView.as_view({
    'post': 'revise',
})

packing_list_detail_view = PackingListDetailView.as_view({
    'get': 'retrieve',
    'patch': 'partial_update',
})

packing_list_finalize_view = PackingListDetailView.as_view({
    'patch': 'finalize',
})

packing_list_revise_view = PackingListDetailView.as_view({
    'post': 'revise',
})

# URL patterns (booking-scoped patterns are included from logistics/urls.py)
urlpatterns = [
    # Commercial Invoice detail
    path(
        '<int:pk>/',
        commercial_invoice_detail_view,
        name='commercial-invoice-detail',
    ),
    path(
        '<int:pk>/finalize/',
        commercial_invoice_finalize_view,
        name='commercial-invoice-finalize',
    ),
    path(
        '<int:pk>/revise/',
        commercial_invoice_revise_view,
        name='commercial-invoice-revise',
    ),
]

packing_list_urlpatterns = [
    # Packing List detail
    path(
        '<int:pk>/',
        packing_list_detail_view,
        name='packing-list-detail',
    ),
    path(
        '<int:pk>/finalize/',
        packing_list_finalize_view,
        name='packing-list-finalize',
    ),
    path(
        '<int:pk>/revise/',
        packing_list_revise_view,
        name='packing-list-revise',
    ),
]

booking_urlpatterns = [
    # Booking-scoped Commercial Invoice
    path(
        '<int:booking_id>/commercial-invoice/',
        booking_commercial_invoice_view,
        name='booking-commercial-invoice',
    ),
    # Booking-scoped Packing List
    path(
        '<int:booking_id>/packing-list/',
        booking_packing_list_view,
        name='booking-packing-list',
    ),
]
