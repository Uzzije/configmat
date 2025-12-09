"""
Configuration values endpoints for Public API v1.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from apps.api_keys.authentication import APIKeyAuthentication
from apps.authentication.models import Tenant
from apps.config_assets.models import ConfigAsset, ConfigObject, ConfigValue
from django.core.cache import cache


class ConfigValuesView(APIView):
    """
    Get configuration values for an asset.
    
    GET /api/v1/organizations/{org}/assets/{asset}/values/?environment={env}
    
    Returns all configuration values for the specified asset and environment.
    Responses are cached for 5 minutes.
    """
    
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, org, asset):
        """
        Get all config values for asset + environment.
        
        Args:
            org: Organization slug
            asset: Asset slug
            
        Query Parameters:
            environment: Environment name (default: 'local')
            
        Returns:
            200 OK: Configuration values
            403 Forbidden: Access denied
            404 Not Found: Organization or asset not found
        """
        environment = request.query_params.get('environment', 'local')
        
        # Check cache first
        cache_key = f"config:{org}:{asset}:{environment}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)
        
        # Get tenant
        try:
            tenant = Tenant.objects.get(slug=org)
        except Tenant.DoesNotExist:
            return Response(
                {'error': f"Organization '{org}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify API key has access to this tenant
        api_key = request.auth
        if api_key.tenant_id != tenant.id:
            return Response(
                {'error': "You don't have access to this organization"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check environment scope
        if api_key.environment and api_key.environment != environment:
            return Response(
                {'error': f"API Key is not authorized for environment '{environment}'"},
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
        
        # Get all config objects and their values
        objects = ConfigObject.objects.filter(asset=asset_obj)
        values_data = {}
        
        for obj in objects:
            values = ConfigValue.objects.filter(
                config_object=obj,
                environment=environment
            )
            
            if values.exists():
                obj_values = {}
                for value in values:
                    if value.value_type == 'json':
                        obj_values[value.key] = value.value_json
                    else:
                        obj_values[value.key] = value.value_string
                
                values_data[obj.name] = obj_values
        
        # Cache for 5 minutes
        cache.set(cache_key, values_data, 300)
        
        return Response(values_data)


class ConfigValueDetailView(APIView):
    """
    Get a specific configuration value from a config object.
    
    GET /api/v1/organizations/{org}/assets/{asset}/objects/{object}/values/{key}/?environment={env}
    
    Returns a single configuration value for granular access.
    Responses are cached for 5 minutes.
    """
    
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, org, asset, object_name, key):
        """
        Get a specific config value.
        
        Args:
            org: Organization slug
            asset: Asset slug
            object_name: Config object name
            key: Configuration key
            
        Query Parameters:
            environment: Environment name (default: 'local')
            
        Returns:
            200 OK: Configuration value
            403 Forbidden: Access denied
            404 Not Found: Organization, asset, object, or key not found
        """
        environment = request.query_params.get('environment', 'local')
        
        # Check cache first
        cache_key = f"config:{org}:{asset}:{object_name}:{key}:{environment}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)
        
        # Get tenant
        try:
            tenant = Tenant.objects.get(slug=org)
        except Tenant.DoesNotExist:
            return Response(
                {'error': f"Organization '{org}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify API key has access to this tenant
        api_key = request.auth
        if api_key.tenant_id != tenant.id:
            return Response(
                {'error': "You don't have access to this organization"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check environment scope
        if api_key.environment and api_key.environment != environment:
            return Response(
                {'error': f"API Key is not authorized for environment '{environment}'"},
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
        
        # Get config object
        try:
            config_obj = ConfigObject.objects.get(asset=asset_obj, name=object_name)
        except ConfigObject.DoesNotExist:
            return Response(
                {'error': f"Config object '{object_name}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get specific value
        try:
            config_value = ConfigValue.objects.get(
                config_object=config_obj,
                key=key,
                environment=environment
            )
        except ConfigValue.DoesNotExist:
            return Response(
                {'error': f"Key '{key}' not found in '{object_name}' for environment '{environment}'"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Prepare response
        if config_value.value_type == 'json':
            value_data = {
                'key': key,
                'value': config_value.value_json,
                'type': 'json',
                'object': object_name,
                'environment': environment
            }
        else:
            value_data = {
                'key': key,
                'value': config_value.value_string,
                'type': 'string',
                'object': object_name,
                'environment': environment
            }
        
        # Cache for 5 minutes
        cache.set(cache_key, value_data, 300)
        
        return Response(value_data)

