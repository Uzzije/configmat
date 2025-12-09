import secrets
from rest_framework import serializers
from .models import APIKey
from apps.config_assets.models import ConfigAsset


class APIKeySerializer(serializers.ModelSerializer):
    key = serializers.CharField(read_only=True)  # Only shown on creation
    asset_slug = serializers.SlugField(write_only=True, required=False, allow_null=True)
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    scope_display = serializers.CharField(source='get_scope_display', read_only=True)

    class Meta:
        model = APIKey
        fields = [
            'id', 'label', 'scope', 'scope_display', 'environment', 'asset_slug', 'asset_name',
            'key_prefix', 'key', 'created_at', 'last_used_at', 'revoked', 'revoked_at'
        ]
        read_only_fields = [
            'id', 'key_prefix', 'created_at', 
            'last_used_at', 'revoked', 'revoked_at'
        ]

    def create(self, validated_data):
        request = self.context['request']
        tenant = request.user.current_tenant or request.user.tenant
        asset_slug = validated_data.pop('asset_slug', None)
        environment = validated_data.get('environment', 'local')
        
        # Determine scope and get asset if needed
        asset = None
        scope = validated_data.get('scope', 'tenant')
        
        if scope == 'asset':
            if not asset_slug:
                raise serializers.ValidationError({"asset_slug": "Asset slug is required for asset-scoped keys"})
            try:
                asset = ConfigAsset.objects.get(slug=asset_slug, tenant=tenant)
            except ConfigAsset.DoesNotExist:
                raise serializers.ValidationError({"asset_slug": "Asset not found"})
        
        # Generate org hash for security
        org_hash = APIKey.generate_org_hash(tenant.slug)
        
        # Generate key in format: cm_<org_hash>_<asset_slug>_<random>
        random_part = secrets.token_urlsafe(16)  # 16 bytes = ~22 chars
        
        if asset:
            raw_key = f"cm_{org_hash}_{asset.slug}_{random_part}"
        else:
            raw_key = f"cm_{org_hash}_{random_part}"
        
        # Hash it for storage
        key_hash = APIKey.hash_key(raw_key)
        
        # Create the API key record
        api_key = APIKey.objects.create(
            tenant=tenant,
            asset=asset,
            scope=scope,
            environment=environment,
            created_by=request.user,
            key_hash=key_hash,
            key_prefix=raw_key[:16],  # cm_abc12345...
            label=validated_data['label']
        )
        
        # Return the raw key ONLY once (via serializer property)
        api_key.key = raw_key
        return api_key
