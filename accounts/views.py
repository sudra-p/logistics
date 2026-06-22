"""
User management views for Admin users.
"""

from django.contrib.auth import get_user_model
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import UserProfile
from accounts.permissions import IsAdminUser
from accounts.serializers import (
    RoleAssignmentSerializer,
    UserCreateSerializer,
    UserProfileSerializer,
    UserSerializer,
)

User = get_user_model()

MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2 MB


class UserViewSet(viewsets.ModelViewSet):
    """
    Admin-only ViewSet for user management.

    - GET /api/accounts/users/ — List all users with roles
    - POST /api/accounts/users/ — Create a user with role assignment
    - GET /api/accounts/users/{id}/ — Retrieve a user
    - GET /api/accounts/users/me/ — Get current user's profile (any authenticated user)
    - PATCH /api/accounts/users/me/ — Update current user's profile
    - POST /api/accounts/users/me/avatar/ — Upload avatar
    - PATCH /api/accounts/users/{id}/role/ — Change user role
    """

    queryset = User.objects.all().order_by('id')

    def get_permissions(self):
        if self.action in ('me', 'upload_avatar'):
            return [IsAuthenticated()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        if self.action == 'me':
            return UserProfileSerializer
        return UserSerializer

    @action(detail=False, methods=['get', 'patch'], url_path='me')
    def me(self, request):
        """
        GET /api/accounts/users/me/ — Return the current authenticated user's profile.
        PATCH /api/accounts/users/me/ — Update the current user's profile fields.
        """
        if request.method == 'PATCH':
            serializer = UserProfileSerializer(
                request.user, data=request.data, partial=True, context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        serializer = UserProfileSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='me/avatar', parser_classes=[MultiPartParser])
    def upload_avatar(self, request):
        """POST /api/accounts/users/me/avatar/ — Upload a profile picture."""
        file = request.FILES.get('avatar')
        if not file:
            return Response(
                {'avatar': ['No file was submitted.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if file.size > MAX_AVATAR_SIZE:
            return Response(
                {'avatar': ['File size must be under 2 MB.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not file.content_type.startswith('image/'):
            return Response(
                {'avatar': ['Only image files are allowed.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.avatar = file
        profile.save()

        avatar_url = request.build_absolute_uri(profile.avatar.url)
        return Response({'avatar_url': avatar_url}, status=status.HTTP_200_OK)

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
