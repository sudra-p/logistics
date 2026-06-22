"""
URL configuration for the logistics project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from logistics.views import health_check
from invoices.urls import booking_urlpatterns as invoice_booking_urls
from invoices.urls import packing_list_urlpatterns as packing_list_urls
from bl.urls import booking_urlpatterns as bl_booking_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health_check'),
    path('api/master-data/', include('master_data.urls', namespace='master_data')),
    path('api/bookings/search/', include('search.urls', namespace='search')),
    path('api/bookings/', include('bookings.urls', namespace='bookings')),
    path('api/reports/', include('reports.urls', namespace='reports')),
    path('api/documents/', include('documents.urls', namespace='documents')),
    path('api/accounts/', include('accounts.urls', namespace='accounts')),
    path('api/proforma-invoices/', include('proforma.urls', namespace='proforma')),
    path('api/payments/', include('payments.urls', namespace='payments')),
    path('api/stock-items/', include('inventory.urls', namespace='inventory')),
    # Commercial Invoice & Packing List
    path('api/commercial-invoices/', include('invoices.urls', namespace='invoices')),
    path('api/packing-lists/', include(packing_list_urls)),
    path('api/bookings/', include(invoice_booking_urls)),
    # Bill of Lading
    path('api/bl/', include('bl.urls', namespace='bl')),
    path('api/bookings/', include(bl_booking_urls)),
    # Dashboard
    path('api/dashboard/', include('dashboard.urls', namespace='dashboard')),
    # Operations Tracking
    path('api/operations/', include('operations.urls', namespace='operations')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

