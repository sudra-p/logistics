from rest_framework.permissions import BasePermission


def _user_in_group(user, group_name):
    """Check if a user belongs to a specific group."""
    return user.groups.filter(name=group_name).exists()


def _is_superuser(user):
    """Check if user is a superuser (bypasses group checks)."""
    return user.is_superuser


class IsOperationsUser(BasePermission):
    """Allows access to users in the Operations group."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (_is_superuser(request.user) or _user_in_group(request.user, 'Operations'))
        )


class IsAccountsUser(BasePermission):
    """Allows access to users in the Accounts group."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (_is_superuser(request.user) or _user_in_group(request.user, 'Accounts'))
        )


class IsSalesUser(BasePermission):
    """Allows access to users in the Sales group."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (_is_superuser(request.user) or _user_in_group(request.user, 'Sales'))
        )


class IsAdminUser(BasePermission):
    """Allows access to users in the Admin group."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (_is_superuser(request.user) or _user_in_group(request.user, 'Admin'))
        )


class CanModifyBooking(BasePermission):
    """
    Allows booking creation and modification.
    Granted to Operations and Admin users.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            _is_superuser(request.user)
            or _user_in_group(request.user, 'Operations')
            or _user_in_group(request.user, 'Admin')
        )


class CanViewBooking(BasePermission):
    """
    Allows read-only access to bookings.
    Granted to Operations, Accounts, Sales, and Admin users.
    Sales users have additional queryset-level filtering applied in views.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            _is_superuser(request.user)
            or _user_in_group(request.user, 'Operations')
            or _user_in_group(request.user, 'Accounts')
            or _user_in_group(request.user, 'Sales')
            or _user_in_group(request.user, 'Admin')
        )


class CanManageMasterData(BasePermission):
    """
    Allows CRUD operations on master data entities.
    Granted only to Admin users.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _is_superuser(request.user) or _user_in_group(request.user, 'Admin')


class CanManageProforma(BasePermission):
    """
    Allows write access to Proforma Invoices.
    Granted to Accounts and Admin users.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            _is_superuser(request.user)
            or _user_in_group(request.user, 'Accounts')
            or _user_in_group(request.user, 'Admin')
        )


class CanViewProforma(BasePermission):
    """
    Allows read access to Proforma Invoices.
    Granted to Accounts, Admin, and Sales users.
    Sales users have additional queryset-level filtering applied in views.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            _is_superuser(request.user)
            or _user_in_group(request.user, 'Accounts')
            or _user_in_group(request.user, 'Admin')
            or _user_in_group(request.user, 'Sales')
        )


class CanManagePayments(BasePermission):
    """
    Allows CRUD operations on Payment records.
    Granted to Accounts and Admin users.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            _is_superuser(request.user)
            or _user_in_group(request.user, 'Accounts')
            or _user_in_group(request.user, 'Admin')
        )


class CanManageInventory(BasePermission):
    """
    Allows CRUD operations on Stock Item records.
    Granted to Operations and Admin users.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            _is_superuser(request.user)
            or _user_in_group(request.user, 'Operations')
            or _user_in_group(request.user, 'Admin')
        )


class CanPerformStuffing(BasePermission):
    """
    Allows performing the container stuffing action.
    Granted to Operations and Admin users.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            _is_superuser(request.user)
            or _user_in_group(request.user, 'Operations')
            or _user_in_group(request.user, 'Admin')
        )


class CanManageDocuments(BasePermission):
    """
    Allows CRUD operations on Commercial Invoices and Packing Lists.
    Granted to Accounts, Operations, and Admin users.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            _is_superuser(request.user)
            or _user_in_group(request.user, 'Accounts')
            or _user_in_group(request.user, 'Operations')
            or _user_in_group(request.user, 'Admin')
        )


class CanManageBL(BasePermission):
    """
    Allows CRUD operations on Bill of Lading records.
    Granted to Operations and Admin users.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            _is_superuser(request.user)
            or _user_in_group(request.user, 'Operations')
            or _user_in_group(request.user, 'Admin')
        )
