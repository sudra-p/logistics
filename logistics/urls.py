"""
URL configuration for the logistics project.
"""

from django.contrib import admin
from django.urls import include, path

from logistics.views import health_check

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health_check'),
    path('api/master-data/', include('master_data.urls', namespace='master_data')),
    path('api/bookings/search/', include('search.urls', namespace='search')),
    path('api/bookings/', include('bookings.urls', namespace='bookings')),
    path('api/reports/', include('reports.urls', namespace='reports')),
    path('api/documents/', include('documents.urls', namespace='documents')),
    path('api/accounts/', include('accounts.urls', namespace='accounts')),
]
