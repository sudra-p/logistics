import pytest

from logistics.pagination import StandardPagination


class TestStandardPagination:
    def test_default_page_size(self):
        pagination = StandardPagination()
        assert pagination.page_size == 25

    def test_max_page_size(self):
        pagination = StandardPagination()
        assert pagination.max_page_size == 100

    def test_page_size_query_param(self):
        pagination = StandardPagination()
        assert pagination.page_size_query_param == 'page_size'
