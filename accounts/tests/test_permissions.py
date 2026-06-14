import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import RequestFactory

from accounts.permissions import (
    CanManageMasterData,
    CanModifyBooking,
    CanViewBooking,
    IsAccountsUser,
    IsAdminUser,
    IsOperationsUser,
    IsSalesUser,
)

User = get_user_model()


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def operations_user(db):
    user = User.objects.create_user(username='ops_user', password='testpass')
    group, _ = Group.objects.get_or_create(name='Operations')
    user.groups.add(group)
    return user


@pytest.fixture
def accounts_user(db):
    user = User.objects.create_user(username='acc_user', password='testpass')
    group, _ = Group.objects.get_or_create(name='Accounts')
    user.groups.add(group)
    return user


@pytest.fixture
def sales_user(db):
    user = User.objects.create_user(username='sales_user', password='testpass')
    group, _ = Group.objects.get_or_create(name='Sales')
    user.groups.add(group)
    return user


@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(username='admin_user', password='testpass')
    group, _ = Group.objects.get_or_create(name='Admin')
    user.groups.add(group)
    return user


@pytest.fixture
def unauthenticated_user():
    from django.contrib.auth.models import AnonymousUser
    return AnonymousUser()


class TestIsOperationsUser:
    def test_grants_access_to_operations_user(self, request_factory, operations_user):
        request = request_factory.get('/')
        request.user = operations_user
        assert IsOperationsUser().has_permission(request, None) is True

    def test_denies_access_to_sales_user(self, request_factory, sales_user):
        request = request_factory.get('/')
        request.user = sales_user
        assert IsOperationsUser().has_permission(request, None) is False

    def test_denies_access_to_unauthenticated(self, request_factory, unauthenticated_user):
        request = request_factory.get('/')
        request.user = unauthenticated_user
        assert IsOperationsUser().has_permission(request, None) is False


class TestIsAccountsUser:
    def test_grants_access_to_accounts_user(self, request_factory, accounts_user):
        request = request_factory.get('/')
        request.user = accounts_user
        assert IsAccountsUser().has_permission(request, None) is True

    def test_denies_access_to_operations_user(self, request_factory, operations_user):
        request = request_factory.get('/')
        request.user = operations_user
        assert IsAccountsUser().has_permission(request, None) is False


class TestIsSalesUser:
    def test_grants_access_to_sales_user(self, request_factory, sales_user):
        request = request_factory.get('/')
        request.user = sales_user
        assert IsSalesUser().has_permission(request, None) is True

    def test_denies_access_to_accounts_user(self, request_factory, accounts_user):
        request = request_factory.get('/')
        request.user = accounts_user
        assert IsSalesUser().has_permission(request, None) is False


class TestIsAdminUser:
    def test_grants_access_to_admin_user(self, request_factory, admin_user):
        request = request_factory.get('/')
        request.user = admin_user
        assert IsAdminUser().has_permission(request, None) is True

    def test_denies_access_to_operations_user(self, request_factory, operations_user):
        request = request_factory.get('/')
        request.user = operations_user
        assert IsAdminUser().has_permission(request, None) is False


class TestCanModifyBooking:
    def test_grants_access_to_operations_user(self, request_factory, operations_user):
        request = request_factory.post('/')
        request.user = operations_user
        assert CanModifyBooking().has_permission(request, None) is True

    def test_grants_access_to_admin_user(self, request_factory, admin_user):
        request = request_factory.post('/')
        request.user = admin_user
        assert CanModifyBooking().has_permission(request, None) is True

    def test_denies_access_to_accounts_user(self, request_factory, accounts_user):
        request = request_factory.post('/')
        request.user = accounts_user
        assert CanModifyBooking().has_permission(request, None) is False

    def test_denies_access_to_sales_user(self, request_factory, sales_user):
        request = request_factory.post('/')
        request.user = sales_user
        assert CanModifyBooking().has_permission(request, None) is False

    def test_denies_access_to_unauthenticated(self, request_factory, unauthenticated_user):
        request = request_factory.post('/')
        request.user = unauthenticated_user
        assert CanModifyBooking().has_permission(request, None) is False


class TestCanViewBooking:
    def test_grants_access_to_all_roles(self, request_factory, operations_user, accounts_user, sales_user, admin_user):
        for user in [operations_user, accounts_user, sales_user, admin_user]:
            request = request_factory.get('/')
            request.user = user
            assert CanViewBooking().has_permission(request, None) is True

    def test_denies_access_to_unauthenticated(self, request_factory, unauthenticated_user):
        request = request_factory.get('/')
        request.user = unauthenticated_user
        assert CanViewBooking().has_permission(request, None) is False


class TestCanManageMasterData:
    def test_grants_access_to_admin_user(self, request_factory, admin_user):
        request = request_factory.post('/')
        request.user = admin_user
        assert CanManageMasterData().has_permission(request, None) is True

    def test_denies_access_to_operations_user(self, request_factory, operations_user):
        request = request_factory.post('/')
        request.user = operations_user
        assert CanManageMasterData().has_permission(request, None) is False

    def test_denies_access_to_sales_user(self, request_factory, sales_user):
        request = request_factory.post('/')
        request.user = sales_user
        assert CanManageMasterData().has_permission(request, None) is False

    def test_denies_access_to_accounts_user(self, request_factory, accounts_user):
        request = request_factory.post('/')
        request.user = accounts_user
        assert CanManageMasterData().has_permission(request, None) is False
