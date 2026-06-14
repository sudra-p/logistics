"""
User management views for Admin users.
"""

from django.contrib.auth import get_user_model
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsAdminUser
from accounts.serializers import RoleAssignmentSerializer, UserCreateSerializer, UserSerializer

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """
    Admin-only ViewSet for user management.

    - GET /api/accounts/users/ — List all users with roles
    - POST /api/accounts/users/ — Create a user with role assignment
    - GET /api/accounts/users/{id}/ — Retrieve a user
    - PATCH /api/accounts/users/{id}/role/ — Change user role
    """

    queryset = User.objects.all().order_by('id')
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        response_serializer = UserSerializer(user)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], url_path='role')
    def assign_role(self, request, pk=None):
        """PATCH /api/accounts/users/{id}/role/ — Change a user's role."""
        user = self.get_object()
        serializer = RoleAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.update(user, serializer.validated_data)
        response_serializer = UserSerializer(user)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
