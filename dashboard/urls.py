from django.urls import path

from dashboard.views import (
    AlertDismissView,
    AlertsView,
    CurrentShipmentsView,
    DocumentStatusView,
    KPIView,
    ProformaStatusView,
    ReadyForBookingView,
)

app_name = 'dashboard'

urlpatterns = [
    path('kpis/', KPIView.as_view(), name='kpis'),
    path('proforma-status/', ProformaStatusView.as_view(), name='proforma-status'),
    path('ready-for-booking/', ReadyForBookingView.as_view(), name='ready-for-booking'),
    path('current-shipments/', CurrentShipmentsView.as_view(), name='current-shipments'),
    path('document-status/', DocumentStatusView.as_view(), name='document-status'),
    path('alerts/', AlertsView.as_view(), name='alerts'),
]

# Separate URL patterns for /api/alerts/ (included in main urls.py at 'api/alerts/')
alert_urlpatterns = [
    path('<int:pk>/dismiss/', AlertDismissView.as_view(), name='alert-dismiss'),
]
