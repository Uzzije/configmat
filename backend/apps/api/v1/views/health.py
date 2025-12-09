"""
Health check endpoint for Public API v1.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from django.utils import timezone


class HealthCheckView(APIView):
    """
    Health check endpoint.
    
    GET /api/v1/health/
    
    Returns the health status of the API and its dependencies.
    No authentication required.
    """
    
    authentication_classes = []
    permission_classes = []
    
    def get(self, request):
        """
        Check system health.
        
        Returns:
            200 OK: System is healthy
            503 Service Unavailable: System is unhealthy
        """
        health_status = {
            'status': 'healthy',
            'service': 'ConfigMat Public API',
            'version': 'v1',
            'timestamp': timezone.now().isoformat()
        }
        
        # Check database connection
        try:
            connection.ensure_connection()
            health_status['database'] = 'connected'
        except Exception as e:
            health_status['database'] = 'disconnected'
            health_status['database_error'] = str(e)
            health_status['status'] = 'unhealthy'
            return Response(
                health_status,
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        return Response(health_status, status=status.HTTP_200_OK)
