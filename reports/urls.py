from django.urls import path

from reports.views import (
    MasterExportView,
    MasterReportView,
    PendingDOExportView,
    PendingDOReportView,
)

app_name = 'reports'

urlpatterns = [
    path('pending-do/', PendingDOReportView.as_view(), name='pending-do'),
    path('pending-do/export/', PendingDOExportView.as_view(), name='pending-do-export'),
    path('master/', MasterReportView.as_view(), name='master'),
    path('master/export/', MasterExportView.as_view(), name='master-export'),
]
