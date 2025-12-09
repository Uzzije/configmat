"""CLI-specific API views for ConfigMat."""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.api_keys.authentication import APIKeyAuthentication
from apps.authentication.models import Tenant
from .models import ConfigAsset, ConfigObject, ConfigValue
from .serializers import ConfigAssetSerializer, ConfigObjectSerializer


class CLIOrganizationAssetsView(APIView):
    """
    List all assets for an organization (CLI endpoint).
    GET /api/organizations/{org_slug}/assets
    """
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, org_slug):
        """List all assets in the organization."""
        # Get the tenant by slug
        try:
            tenant = Tenant.objects.get(slug=org_slug)
        except Tenant.DoesNotExist:
            return Response(
                {"error": f"Organization '{org_slug}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verify user has access to this tenant
        api_key = request.auth
        if api_key.tenant_id != tenant.id:
            return Response(
                {"error": "You don't have access to this organization"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get all assets for this tenant
        assets = ConfigAsset.objects.filter(tenant=tenant).order_by('name')
        
        # Serialize with nested objects
        assets_data = []
        for asset in assets:
            objects = ConfigObject.objects.filter(asset=asset).order_by('name')
            
            assets_data.append({
                "id": str(asset.id),
                "slug": asset.slug,
                "name": asset.name,
                "description": asset.description or "",
                "context": asset.context or "",
                "context_type": asset.context_type or "",
                "objects": [
                    {
                        "id": str(obj.id),
                        "slug": obj.name,  # ConfigObject uses 'name' not 'slug'
                        "name": obj.name,
                        "type": obj.object_type,
                        "description": obj.description or ""
                    }
                    for obj in objects
                ]
            })

        return Response({"assets": assets_data})


class CLIAssetDetailView(APIView):
    """
    Get details of a specific asset (CLI endpoint).
    GET /api/organizations/{org_slug}/assets/{asset_slug}
    """
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, org_slug, asset_slug):
        """Get asset details with all objects."""
        # Get the tenant by slug
        try:
            tenant = Tenant.objects.get(slug=org_slug)
        except Tenant.DoesNotExist:
            return Response(
                {"error": f"Organization '{org_slug}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verify user has access to this tenant
        api_key = request.auth
        if api_key.tenant_id != tenant.id:
            return Response(
                {"error": "You don't have access to this organization"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get the asset
        try:
            asset = ConfigAsset.objects.get(tenant=tenant, slug=asset_slug)
        except ConfigAsset.DoesNotExist:
            return Response(
                {"error": f"Asset '{asset_slug}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get all objects for this asset
        objects = ConfigObject.objects.filter(asset=asset).order_by('name')

        asset_data = {
            "id": str(asset.id),
            "slug": asset.slug,
            "name": asset.name,
            "description": asset.description or "",
            "context": asset.context or "",
            "context_type": asset.context_type or "",
            "objects": [
                {
                    "id": str(obj.id),
                    "slug": obj.name,  # ConfigObject uses 'name' not 'slug'
                    "name": obj.name,
                    "type": obj.object_type,
                    "description": obj.description or ""
                }
                for obj in objects
            ]
        }

        return Response(asset_data)


class CLIAssetValuesView(APIView):
    """
    Get configuration values for an asset (CLI endpoint).
    GET /api/organizations/{org_slug}/assets/{asset_slug}/values?environment=local
    """
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, org_slug, asset_slug):
        """Get all configuration values for an asset in a specific environment."""
        environment = request.query_params.get('environment', 'local')

        # Get the tenant by slug
        try:
            tenant = Tenant.objects.get(slug=org_slug)
        except Tenant.DoesNotExist:
            return Response(
                {"error": f"Organization '{org_slug}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verify user has access to this tenant
        api_key = request.auth
        if api_key.tenant_id != tenant.id:
            return Response(
                {"error": "You don't have access to this organization"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check environment scope if API key has one
        if api_key.environment and api_key.environment != environment:
            return Response(
                {"error": f"API Key is not authorized for environment '{environment}'"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get the asset
        try:
            asset = ConfigAsset.objects.get(tenant=tenant, slug=asset_slug)
        except ConfigAsset.DoesNotExist:
            return Response(
                {"error": f"Asset '{asset_slug}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get all objects and their values for this asset
        objects = ConfigObject.objects.filter(asset=asset)
        
        values_data = {}
        for obj in objects:
            # Get all values for this object in the specified environment
            values = ConfigValue.objects.filter(
                config_object=obj,
                environment=environment
            )
            
            if values.exists():
                obj_values = {}
                for value in values:
                    # Get the actual value based on type
                    if value.value_type == 'json':
                        obj_values[value.key] = value.value_json
                    else:
                        obj_values[value.key] = value.value_string
                
                values_data[obj.name] = obj_values  # ConfigObject uses 'name' not 'slug'

        return Response(values_data)


class CLIHealthCheckView(APIView):
    """
    Health check endpoint for CLI.
    GET /api/health
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        """Simple health check."""
        return Response({
            "status": "healthy",
            "service": "ConfigMat API"
        })
