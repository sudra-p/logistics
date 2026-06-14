from rest_framework import status, viewsets
from rest_framework.exceptions import NotFound
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import CanManageMasterData

from .serializers import ENTITY_SERIALIZER_MAP


class MasterDataViewSet(viewsets.ModelViewSet):
    """
    Generic ViewSet for all master data entity types.

    Permissions:
    - Read (list/retrieve): Any authenticated user.
    - Create/Update/Delete: Admin only (CanManageMasterData).

    Supports:
    - Filtering by name (case-insensitive contains) via `?name=` query param.
    - Ordering by `name` or `created_at` via `?ordering=` query param.
    - Pagination via the project's StandardPagination.

    Deletion protection:
    - Returns 409 Conflict if the entity is referenced by any booking-related record.
    """

    filter_backends = [OrderingFilter]
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_permissions(self):
        """
        Admin-only for create/update/delete.
        Any authenticated user can read.
        """
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), CanManageMasterData()]
        return [IsAuthenticated()]

    def _get_entity_config(self):
        """Resolve the entity type from the URL kwargs."""
        entity_type = self.kwargs.get('entity_type', '')
        serializer_class = ENTITY_SERIALIZER_MAP.get(entity_type)
        if serializer_class is None:
            raise NotFound(
                detail=f"Unknown entity type: '{entity_type}'. "
                f"Valid types are: {', '.join(sorted(ENTITY_SERIALIZER_MAP.keys()))}"
            )
        return serializer_class

    def get_serializer_class(self):
        return self._get_entity_config()

    def get_queryset(self):
        serializer_class = self._get_entity_config()
        model = serializer_class.Meta.model
        queryset = model.objects.all()

        # Filter by name (case-insensitive contains)
        name_filter = self.request.query_params.get('name')
        if name_filter:
            queryset = queryset.filter(name__icontains=name_filter)

        return queryset

    def perform_destroy(self, instance):
        """
        Deletion protection: reject delete if the entity is referenced
        by any booking-related record (Booking, Container, TranshipmentLeg).
        Uses Django's reverse relation introspection.
        """
        model = instance.__class__
        # Check all related objects that reference this instance
        for related_object in model._meta.get_fields():
            if not related_object.one_to_many and not related_object.one_to_one:
                continue
            # Skip reverse relations that are not from booking-related models
            if not hasattr(related_object, 'related_model'):
                continue
            related_model = related_object.related_model
            related_app = related_model._meta.app_label
            if related_app != 'bookings':
                continue
            # Check if any related booking record references this instance
            accessor_name = related_object.get_accessor_name()
            related_manager = getattr(instance, accessor_name)
            if related_manager.exists():
                return Response(
                    {
                        'detail': (
                            f"Cannot delete this {model._meta.verbose_name}. "
                            f"It is referenced by existing "
                            f"{related_model._meta.verbose_name_plural}."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
        instance.delete()

    def destroy(self, request, *args, **kwargs):
        """
        Override destroy to handle the 409 Conflict response from perform_destroy.
        """
        instance = self.get_object()
        response = self.perform_destroy(instance)
        if response is not None:
            return response
        return Response(status=status.HTTP_204_NO_CONTENT)
