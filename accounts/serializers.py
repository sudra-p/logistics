"""
Serializers for user management endpoints.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import serializers

User = get_user_model()

VALID_ROLES = ['Admin', 'Operations', 'Accounts', 'Sales']


class UserSerializer(serializers.ModelSerializer):
    """Serializer for listing users with their roles."""

    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'role']
        read_only_fields = ['id']

    def get_role(self, obj):
        """Return the user's group name (role)."""
        group = obj.groups.first()
        return group.name if group else None


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a user with a role assignment."""

    role = serializers.ChoiceField(choices=VALID_ROLES, write_only=True)
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'role']

    def create(self, validated_data):
        role_name = validated_data.pop('role')
        password = validated_data.pop('password')

        user = User(**validated_data)
        user.set_password(password)
        user.save()

        group, _ = Group.objects.get_or_create(name=role_name)
        user.groups.add(group)

        return user


class RoleAssignmentSerializer(serializers.Serializer):
    """Serializer for changing a user's role."""

    role = serializers.ChoiceField(choices=VALID_ROLES)

    def update(self, user, validated_data):
        """Replace the user's current groups with the new role."""
        role_name = validated_data['role']
        group, _ = Group.objects.get_or_create(name=role_name)

        # Remove existing role groups and assign new one
        user.groups.clear()
        user.groups.add(group)

        return user
