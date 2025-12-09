from rest_framework import serializers
from .org_models import ContextType, Environment
from .models import Tenant


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['id', 'name', 'slug', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']


class ContextTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContextType
        fields = ['id', 'type', 'category', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Automatically set tenant from request context
        validated_data['tenant'] = self.context['request'].user.current_tenant or self.context['request'].user.tenant
        return super().create(validated_data)


class EnvironmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Environment
        fields = ['id', 'name', 'slug', 'order', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Automatically set tenant from request context
        validated_data['tenant'] = self.context['request'].user.current_tenant or self.context['request'].user.tenant
        return super().create(validated_data)

    def validate_slug(self, value):
        """Ensure slug is lowercase and URL-friendly"""
        if not value.islower():
            raise serializers.ValidationError("Slug must be lowercase")
        if not value.replace('-', '').replace('_', '').isalnum():
            raise serializers.ValidationError("Slug can only contain letters, numbers, hyphens, and underscores")
        return value
