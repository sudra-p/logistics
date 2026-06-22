from django.urls import include, path
from rest_framework.routers import DefaultRouter

from payments.views import PaymentViewSet

app_name = 'payments'

router = DefaultRouter()
router.register('', PaymentViewSet, basename='payment')

urlpatterns = [
    path('', include(router.urls)),
]
