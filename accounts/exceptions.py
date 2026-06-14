"""
Custom exception handler to ensure proper HTTP status codes:
- 401 for unauthenticated requests
- 403 for unauthorized (insufficient permissions)
"""

from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """
    Custom exception handler that ensures:
    - NotAuthenticated and AuthenticationFailed return 401
    - PermissionDenied returns 403
    """
    response = exception_handler(exc, context)

    if response is not None:
        if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
            response.status_code = status.HTTP_401_UNAUTHORIZED

    return response
