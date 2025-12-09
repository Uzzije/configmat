"""
Asset endpoints for Public API v1.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from apps.api_keys.authentication import APIKeyAuthentication
from apps.authentication.models import Tenant
from apps.config_assets.models import ConfigAsset, ConfigObject


class AssetListView(APIView):
    """
    List all assets in an organization.
    
    GET /api/v1/organizations/{org}/assets/
    
    Returns a list of all assets the API key has access to.
    """
    
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, org):
        """
        List all assets.
        
        Args:
            org: Organization slug
            
        Returns:
            200 OK: List of assets
            403 Forbidden: Access denied
            404 Not Found: Organization not found
        """
        # Get tenant
        try:
            tenant = Tenant.objects.get(slug=org)
        except Tenant.DoesNotExist:
            return Response(
                {'error': f"Organization '{org}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify access
        api_key = request.auth
        if api_key.tenant_id != tenant.id:
            return Response(
                {'error': "You don't have access to this organization"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get assets
        assets = ConfigAsset.objects.filter(tenant=tenant).order_by('name')
        
        assets_data = [
            {
                'id': str(asset.id),
                'slug': asset.slug,
                'name': asset.name,
                'description': asset.description or ''
            }
            for asset in assets
        ]
        
        return Response({'assets': assets_data})


class AssetDetailView(APIView):
    """
    Get details of a specific asset.
    
    GET /api/v1/organizations/{org}/assets/{asset}/
    
    Returns detailed information about an asset.
    """
    
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, org, asset):
        """
        Get asset details.
        
        Args:
            org: Organization slug
            asset: Asset slug
            
        Returns:
            200 OK: Asset details
            403 Forbidden: Access denied
            404 Not Found: Organization or asset not found
        """
        # Get tenant
        try:
            tenant = Tenant.objects.get(slug=org)
        except Tenant.DoesNotExist:
            return Response(
                {'error': f"Organization '{org}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify access
        api_key = request.auth
        if api_key.tenant_id != tenant.id:
            return Response(
                {'error': "You don't have access to this organization"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get asset
        try:
            asset_obj = ConfigAsset.objects.get(tenant=tenant, slug=asset)
        except ConfigAsset.DoesNotExist:
            return Response(
                {'error': f"Asset '{asset}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get config objects
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
                    'description': obj.description or ''
                }
                for obj in objects
            ]
        }
        
        return Response(asset_data)
