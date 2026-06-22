from django.urls import include, path
from rest_framework.routers import DefaultRouter

from inventory.views import StockItemViewSet

app_name = 'inventory'

router = DefaultRouter()
router.register('', StockItemViewSet, basename='stock-item')

urlpatterns = [
    path('', include(router.urls)),
]
