from django.urls import include, path
from rest_framework.routers import DefaultRouter

from proforma.views import ProformaInvoiceViewSet

app_name = 'proforma'

router = DefaultRouter()
router.register('', ProformaInvoiceViewSet, basename='proforma-invoice')

urlpatterns = [
    path('', include(router.urls)),
]
