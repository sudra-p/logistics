import pytest

from master_data.models import BaseEntity


class TestBaseEntity:
    def test_is_abstract(self):
        """BaseEntity should be an abstract model - cannot be instantiated directly."""
        assert BaseEntity._meta.abstract is True

    def test_has_required_fields(self):
        """BaseEntity should define name, is_active, created_at, and updated_at fields."""
        field_names = [f.name for f in BaseEntity._meta.get_fields()]
        assert 'name' in field_names
        assert 'is_active' in field_names
        assert 'created_at' in field_names
        assert 'updated_at' in field_names

    def test_name_field_max_length(self):
        name_field = BaseEntity._meta.get_field('name')
        assert name_field.max_length == 255

    def test_name_field_unique(self):
        name_field = BaseEntity._meta.get_field('name')
        assert name_field.unique is True

    def test_is_active_default_true(self):
        is_active_field = BaseEntity._meta.get_field('is_active')
        assert is_active_field.default is True

    def test_created_at_auto_now_add(self):
        created_at_field = BaseEntity._meta.get_field('created_at')
        assert created_at_field.auto_now_add is True

    def test_updated_at_auto_now(self):
        updated_at_field = BaseEntity._meta.get_field('updated_at')
        assert updated_at_field.auto_now is True

    def test_default_ordering(self):
        assert BaseEntity._meta.ordering == ['name']
