from django.urls import include, path
from rest_framework.routers import DefaultRouter

from bookings.views import (
    BookingViewSet,
    ContainerDetailView,
    ContainerListCreateView,
    TranshipmentDetailView,
    TranshipmentListCreateView,
)
from documents.views import (
    AttachmentDeleteView,
    AttachmentDownloadView,
    AttachmentListCreateView,
    BLDraftView,
    DODraftView,
)
from inventory.views import StuffingView

app_name = 'bookings'

router = DefaultRouter()
router.register('', BookingViewSet, basename='booking')

urlpatterns = [
    # Container endpoints (must be before router.urls to avoid conflicts)
    path(
        '<int:booking_id>/containers/',
        ContainerListCreateView.as_view(),
        name='container-list-create',
    ),
    path(
        '<int:booking_id>/containers/<int:container_id>/',
        ContainerDetailView.as_view(),
        name='container-detail',
    ),
    # Container stuffing endpoint
    path(
        '<int:booking_id>/containers/<int:container_id>/stuff/',
        StuffingView.as_view(),
        name='container-stuff',
    ),
    # Transhipment endpoints (must be before router.urls to avoid conflicts)
    path(
        '<int:booking_id>/transhipments/',
        TranshipmentListCreateView.as_view(),
        name='transhipment-list-create',
    ),
    path(
        '<int:booking_id>/transhipments/<int:leg_id>/',
        TranshipmentDetailView.as_view(),
        name='transhipment-detail',
    ),
    # Attachment endpoints
    path(
        '<int:booking_id>/attachments/',
        AttachmentListCreateView.as_view(),
        name='attachment-list-create',
    ),
    path(
        '<int:booking_id>/attachments/<int:attachment_id>/download/',
        AttachmentDownloadView.as_view(),
        name='attachment-download',
    ),
    path(
        '<int:booking_id>/attachments/<int:attachment_id>/',
        AttachmentDeleteView.as_view(),
        name='attachment-delete',
    ),
    # Document generation endpoints
    path(
        '<int:booking_id>/documents/do-draft/',
        DODraftView.as_view(),
        name='do-draft',
    ),
    path(
        '<int:booking_id>/documents/bl-draft/',
        BLDraftView.as_view(),
        name='bl-draft',
    ),
    # Router-generated booking CRUD endpoints
    path('', include(router.urls)),
]
