"""
Simplified assets endpoints for Public API v1.
Endpoints only require API key - organization is derived from the key.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from apps.api_keys.authentication import APIKeyAuthentication
from apps.config_assets.models import ConfigAsset, ConfigObject


class AssetListView(APIView):
    """
    List all assets in the organization.
    
    GET /api/v1/assets/
    
    Organization is automatically determined from API key.
    """
    
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        List all assets for the organization.
        
        Returns:
            200 OK: List of assets
        """
        # Get tenant from API key
        api_key = request.auth
        tenant = api_key.tenant
        
        # Get all assets for this tenant
        assets = ConfigAsset.objects.filter(tenant=tenant).order_by('name')
        
        assets_data = {
            'assets': [
                {
                    'id': str(asset.id),
                    'slug': asset.slug,
                    'name': asset.name,
                    'description': asset.description or '',
                }
                for asset in assets
            ]
        }
        
        return Response(assets_data)


class AssetDetailView(APIView):
    """
    Get details for a specific asset.
    
    GET /api/v1/assets/{asset}/
    
    Organization is automatically determined from API key.
    """
    
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, asset):
        """
        Get asset details.
        
        Args:
            asset: Asset slug
            
        Returns:
            200 OK: Asset details
            404 Not Found: Asset not found
        """
        # Get tenant from API key
        api_key = request.auth
        tenant = api_key.tenant
        
        # Get asset
        try:
            asset_obj = ConfigAsset.objects.get(tenant=tenant, slug=asset)
        except ConfigAsset.DoesNotExist:
            return Response(
                {'error': f"Asset '{asset}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get config objects for this asset
        objects = ConfigObject.objects.filter(asset=asset_obj).order_by('name')
        
        asset_data = {
            'id': str(asset_obj.id),
            'slug': asset_obj.slug,
            'name': asset_obj.name,
            'description': asset_obj.description or '',
            'objects': [
                {
                    'id': str(obj.id),
                    'name': obj.name,
                    'type': obj.object_type,
                    'description': obj.description or '',
                }
                for obj in objects
            ]
        }
        
        return Response(asset_data)
