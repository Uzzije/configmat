"""
Simplified configuration values endpoints for Public API v1.
Endpoints only require API key - organization is derived from the key.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.core.permissions import HasAPIKey, TenantContextPermission
from apps.api_keys.authentication import APIKeyAuthentication
from apps.config_assets.models import ConfigAsset, ConfigObject, ConfigValue
from django.core.cache import cache

from django.db import transaction

class ConfigValuesView(APIView):
    """
    Get configuration values for an asset.
    
    GET /api/v1/assets/{asset}/values/?environment={env}
    
    Organization is automatically determined from API key.
    """
    
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [HasAPIKey, TenantContextPermission]
    
    def get(self, request, asset):
        """
        Get all config values for asset + environment.
        
        Args:
            asset: Asset slug
            
        Query Parameters:
            environment: Environment name (default: 'local')
            
        Returns:
            200 OK: Configuration values
            403 Forbidden: Environment scope mismatch
            404 Not Found: Asset not found
        """
        # Get tenant and environment from API key
        api_key = request.auth
        tenant = api_key.tenant
        
        # Environment check
        requested_env = request.query_params.get('environment')
        if api_key.environment:
            if requested_env and requested_env != api_key.environment:
                return Response(
                    {'error': f"API Key is not authorized for environment '{requested_env}'"},
                    status=status.HTTP_403_FORBIDDEN
                )
            environment = api_key.environment
        else:
            environment = requested_env or 'local'
        
        # Check cache first
        cache_key = f"config:{tenant.slug}:{asset}:{environment}"
        cached_data = cache.get(cache_key)
        cached_data = cache.get(cache_key)
        if cached_data is not None:
             # Cache Hit
             return Response(cached_data)
        
        # Cache Miss
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

    def post(self, request, asset):
        """
        Update/Create config values for asset + environment.
        Expects JSON payload: { "KEY": { "value": "val", "type": "string|encrypted" }, ... }
        """
        api_key = request.auth
        tenant = api_key.tenant
        
        # Environment check (POST requires explicit env query param or defaults to local)
        requested_env = request.query_params.get('environment')
        if api_key.environment:
            if requested_env and requested_env != api_key.environment:
                return Response({'error': 'Environment mismatch'}, status=403)
            environment = api_key.environment
        else:
            environment = requested_env or 'local'

        try:
             asset_obj = ConfigAsset.objects.get(tenant=tenant, slug=asset)
        except ConfigAsset.DoesNotExist:
             return Response({'error': 'Asset not found'}, status=404)

        data = request.data
        if not isinstance(data, dict):
            return Response({'error': 'Invalid payload'}, status=400)

        # We assume values belong to a "Default" object if not specified, 
        # but the payload is flat keys. 
        # Simple strategy: Find or create a ConfigObject named "default" (or "app") for this asset.
        
        with transaction.atomic():
            # Get/Create default object
            default_obj, created = ConfigObject.objects.get_or_create(
                asset=asset_obj,
                name='app', # Default object name for flat configs
                defaults={'object_type': 'kv'}
            )

            for key, item in data.items():
                val = item.get('value')
                val_type = item.get('type', 'string')
                
                # Create/Update ConfigValue
                cv, created = ConfigValue.objects.get_or_create(
                    config_object=default_obj,
                    environment=environment,
                    key=key,
                    defaults={'value_type': 'string'} # Default
                )
                
                if val_type == 'encrypted':
                     # Value is base64 encoded string of encrypted bytes
                     import base64
                     try:
                         # We store the raw encrypted bytes in `value_encrypted`
                         # The client sends base64, we decode to bytes.
                         encrypted_bytes = base64.b64decode(val)
                         cv.value_encrypted = encrypted_bytes
                         cv.value_string = None # Clear plaintext
                         cv.value_type = 'string' # It's still a string conceptually, just encrypted storage
                     except Exception as e:
                         pass
                else:
                    cv.value_string = str(val)
                    cv.value_encrypted = None
                
                cv.save()

        # Invalidate Cache
        cache_key = f"config:{tenant.slug}:{asset}:{environment}"
        cache.delete(cache_key)

        return Response({'status': 'updated', 'count': len(data)})


class ConfigValueDetailView(APIView):
    """
    Get a specific configuration value from a config object.
    
    GET /api/v1/assets/{asset}/objects/{object}/values/{key}/?environment={env}
    
    Organization is automatically determined from API key.
    """
    
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [HasAPIKey, TenantContextPermission]
    
    def get(self, request, asset, object_name, key):
        """
        Get a specific config value.
        
        Args:
            asset: Asset slug
            object_name: Config object name
            key: Configuration key
            
        Query Parameters:
            environment: Environment name (default: 'local')
            
        Returns:
            200 OK: Configuration value
            403 Forbidden: Environment scope mismatch
            404 Not Found: Asset, object, or key not found
        """
        # Get tenant and environment from API key
        api_key = request.auth
        tenant = api_key.tenant
        
        # Environment check
        requested_env = request.query_params.get('environment')
        if api_key.environment:
            if requested_env and requested_env != api_key.environment:
                return Response(
                    {'error': f"API Key is not authorized for environment '{requested_env}'"},
                    status=status.HTTP_403_FORBIDDEN
                )
            environment = api_key.environment
        else:
            environment = requested_env or 'local'
        
        # Check cache first
        cache_key = f"config:{tenant.slug}:{asset}:{object_name}:{key}:{environment}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)
        
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
