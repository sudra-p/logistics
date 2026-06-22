from django.urls import path

from .views import OperationsTrackingView

app_name = 'operations'

urlpatterns = [
    path('', OperationsTrackingView.as_view(), name='operations-list'),
]
