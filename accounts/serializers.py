"""
Serializers for user management endpoints.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import serializers

from accounts.models import UserProfile

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
        """Return the user's group name (role). Superusers default to Admin."""
        if obj.is_superuser:
            return 'Admin'
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


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile (GET /me/ and PATCH /me/)."""

    role = serializers.SerializerMethodField()
    phone = serializers.CharField(source='profile.phone', required=False, allow_blank=True)
    department = serializers.CharField(source='profile.department', required=False, allow_blank=True)
    avatar_url = serializers.SerializerMethodField()
    marketing_person_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'phone', 'department', 'avatar_url', 'marketing_person_id',
        ]
        read_only_fields = ['id', 'username', 'role', 'avatar_url', 'marketing_person_id']

    def get_role(self, obj):
        if obj.is_superuser:
            return 'Admin'
        group = obj.groups.first()
        return group.name if group else None

    def get_avatar_url(self, obj):
        profile = getattr(obj, 'profile', None)
        if profile and profile.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(profile.avatar.url)
            return profile.avatar.url
        return None

    def get_marketing_person_id(self, obj):
        if hasattr(obj, 'marketing_person'):
            return obj.marketing_person.id
        return None

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})

        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update profile fields
        if profile_data:
            profile, _ = UserProfile.objects.get_or_create(user=instance)
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()

        return instance
