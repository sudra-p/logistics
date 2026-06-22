from django.urls import path

from .views import BLDetailView, BookingBLView

app_name = 'bl'

# Booking-scoped BL endpoint
booking_bl_view = BookingBLView.as_view({
    'get': 'list',
    'post': 'create',
})

# Detail endpoints
bl_detail_view = BLDetailView.as_view({
    'get': 'retrieve',
    'patch': 'partial_update',
})

bl_status_view = BLDetailView.as_view({
    'patch': 'change_status',
})

urlpatterns = [
    path('<int:pk>/', bl_detail_view, name='bl-detail'),
    path('<int:pk>/status/', bl_status_view, name='bl-status'),
]

booking_urlpatterns = [
    path('<int:booking_id>/bl/', booking_bl_view, name='booking-bl'),
]
