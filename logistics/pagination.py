from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """
    Custom pagination class that enforces:
    - Default page size: 25
    - Maximum page size: 100
    - Clients can request a custom page size via the 'page_size' query param.
    """

    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100
