"""
Core views for the logistics project.
"""

from django.db import connection
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint for load balancer and monitoring.
    Returns 200 if the application is running and can connect to the database.
    Does not require authentication.
    """
    health = {
        'status': 'ok',
        'version': '1.0.0',
    }

    # Check database connectivity
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        health['database'] = 'connected'
    except Exception:
        health['status'] = 'degraded'
        health['database'] = 'unavailable'
        return JsonResponse(health, status=503)

    return JsonResponse(health, status=200)
