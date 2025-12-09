from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import ConfigAsset, ConfigObject, ConfigValue, ConfigVersion
from .serializers import (
    ConfigAssetSerializer, ConfigObjectSerializer, 
    ConfigValueSerializer, ConfigVersionSerializer
)
from apps.audit.services import log_activity


from rest_framework.views import APIView
from apps.api_keys.authentication import APIKeyAuthentication
from .services import get_resolved_config

class PublicConfigView(APIView):
    """
    Public endpoint to fetch configuration.
    Requires X-API-Key header.
    """
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [permissions.IsAuthenticated] # APIKeyAuth sets request.user

    def get(self, request, environment, asset_slug):
        # APIKeyAuthentication sets request.auth to the APIKey instance
        api_key = request.auth
        
        # Ensure the API key belongs to the same tenant as the requested asset
        # (Implicitly handled since we resolve using api_key.tenant_id)
        
        # Check environment scope
        if api_key.environment and api_key.environment != environment:
             return Response(
                {"error": f"API Key is not authorized for environment '{environment}'"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        config = get_resolved_config(
            asset_slug=asset_slug,
            environment=environment,
            tenant_id=api_key.tenant_id
        )
        
        if config is None:
            return Response(
                {"error": "Config asset not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
            
        return Response(config)


class ConfigAssetViewSet(viewsets.ModelViewSet):
    """CRUD for Config Assets"""
    serializer_class = ConfigAssetSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['context_type', 'context']
    search_fields = ['name', 'slug', 'description', 'context', 'context_type']
    ordering_fields = ['updated_at', 'name']
    ordering = ['-updated_at']
    lookup_field = 'slug'

    def get_queryset(self):
        # Filter by user's current tenant (or default if not set)
        tenant = self.request.user.current_tenant or self.request.user.tenant
        return ConfigAsset.objects.filter(tenant=tenant)

    def perform_create(self, serializer):
        tenant = self.request.user.current_tenant or self.request.user.tenant
        asset = serializer.save(tenant=tenant)
        log_activity(
            user=self.request.user,
            action="Created Asset",
            target=asset.name,
            details={"slug": asset.slug}
        )

    def perform_destroy(self, instance):
        log_activity(
            user=self.request.user,
            action="Deleted Asset",
            target=instance.name,
            details={"slug": instance.slug}
        )
        instance.delete()

    @action(detail=True, methods=['post'])
    def promote(self, request, slug=None):
        """Promote asset to next environment"""
        asset = self.get_object()
        from_env = request.data.get('from_env')
        to_env = request.data.get('to_env')
        
        if not from_env or not to_env:
            return Response(
                {"error": "from_env and to_env are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Run promotion synchronously (no Redis required)
        from .services import promote_asset
        success = promote_asset(str(asset.id), from_env, to_env, str(request.user.id))
        
        if success:
            return Response(
                {"message": f"Successfully promoted from {from_env} to {to_env}"},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"error": "Promotion failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ConfigObjectViewSet(viewsets.ModelViewSet):
    """CRUD for Config Objects"""
    serializer_class = ConfigObjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['object_type', 'asset']

    def get_queryset(self):
        tenant = self.request.user.current_tenant or self.request.user.tenant
        return ConfigObject.objects.filter(asset__tenant=tenant)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Pass environment query param to serializer
        context['environment'] = self.request.query_params.get('env')
        return context

    def perform_create(self, serializer):
        obj = serializer.save()
        log_activity(
            user=self.request.user,
            action="Created Config Object",
            target=f"{obj.name} (in {obj.asset.name})",
            details={"asset": obj.asset.slug, "type": obj.object_type}
        )

    def perform_destroy(self, instance):
        log_activity(
            user=self.request.user,
            action="Deleted Config Object",
            target=f"{instance.name} (in {instance.asset.name})",
            details={"asset": instance.asset.slug}
        )
        instance.delete()

    @action(detail=True, methods=['post'], url_path='update-values')
    def update_values(self, request, pk=None):
        """Update values for a specific environment"""
        config_object = self.get_object()
        environment = request.data.get('environment')
        values_data = request.data.get('values', [])
        
        if not environment:
            return Response(
                {"error": "environment is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update values
        updated_values = []
        for val_data in values_data:
            key = val_data.get('key')
            value_obj, created = ConfigValue.objects.update_or_create(
                config_object=config_object,
                environment=environment,
                key=key,
                defaults={
                    'value_type': val_data.get('value_type', 'string'),
                    'value_string': val_data.get('value_string'),
                    'value_json': val_data.get('value_json'),
                    'value_reference_id': val_data.get('value_reference_id')
                }
            )
            updated_values.append(value_obj)

        # Create version snapshot
        from .services import create_config_version, invalidate_config_cache
        create_config_version(
            config_object=config_object,
            environment=environment,
            user_id=request.user.id,
            change_summary="Updated via API"
        )
        
        log_activity(
            user=request.user,
            action="Updated Config Values",
            target=f"{config_object.name} ({environment})",
            details={
                "asset": config_object.asset.slug,
                "environment": environment
            }
        )

        serializer = ConfigValueSerializer(updated_values, many=True)
        
        # Invalidate cache
        invalidate_config_cache(config_object.asset.id, environment)
        
        return Response(serializer.data)


class ConfigVersionViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only view for version history"""
    serializer_class = ConfigVersionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['environment']
    ordering_fields = ['version_number', 'updated_at']

    def get_queryset(self):
        tenant = self.request.user.current_tenant or self.request.user.tenant
        return ConfigVersion.objects.filter(
            config_object__asset__tenant=tenant
        )

    @action(detail=True, methods=['post'])
    def rollback(self, request, pk=None):
        """Rollback to this version"""
        from .services import rollback_to_version
        
        success = rollback_to_version(pk, request.user.id)
        
        if success:
            return Response(
                {"message": "Successfully rolled back"},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"error": "Rollback failed"},
                status=status.HTTP_400_BAD_REQUEST
            )
