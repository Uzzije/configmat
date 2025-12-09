"""
API Key metadata endpoint for Public API v1.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from apps.api_keys.authentication import APIKeyAuthentication


class APIKeyMetadataView(APIView):
    """
    Get metadata about the authenticated API key.
    
    GET /api/v1/me/
    
    Returns information about the API key being used, including
    organization slug and environment scope.
    """
    
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Get API key metadata.
        
        Returns:
            200 OK: API key metadata
            403 Forbidden: No/invalid API key
        """
        api_key = request.auth
        
        metadata = {
            'organization': api_key.tenant.slug,
            'environment': api_key.environment,
            'scope': api_key.scope,
            'label': api_key.label,
        }
        
        # Add asset info if key is asset-scoped
        if api_key.scope == 'asset' and api_key.asset:
            metadata['asset'] = api_key.asset.slug
        
        return Response(metadata)
