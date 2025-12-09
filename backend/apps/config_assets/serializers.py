from rest_framework import serializers
from .models import ConfigAsset, ConfigObject, ConfigValue, ConfigVersion
from apps.authentication.serializers import UserSerializer


class ConfigValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfigValue
        fields = [
            'id', 'environment', 'key', 'value_type', 
            'value_string', 'value_json', 'value_reference',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, data):
        """Validate value matches type"""
        value_type = data.get('value_type')
        
        if value_type == 'json' and not data.get('value_json'):
            if not data.get('value_json') == {}: # Allow empty dict
                raise serializers.ValidationError("value_json is required for json type")
        
        if value_type == 'reference' and not data.get('value_reference'):
            raise serializers.ValidationError("value_reference is required for reference type")
            
        return data


class ConfigObjectSerializer(serializers.ModelSerializer):
    values = serializers.SerializerMethodField()
    
    class Meta:
        model = ConfigObject
        fields = [
            'id', 'asset', 'name', 'object_type', 
            'description', 'values', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_values(self, obj):
        # Filter values by environment if provided in context
        environment = self.context.get('environment')
        values = obj.values.all()
        if environment:
            values = values.filter(environment=environment)
        return ConfigValueSerializer(values, many=True).data


class ConfigAssetSerializer(serializers.ModelSerializer):
    config_objects = ConfigObjectSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)

    class Meta:
        model = ConfigAsset
        fields = [
            'id', 'tenant', 'tenant_name', 'name', 'slug', 
            'description', 'context_type', 'context', 
            'config_objects', 'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'tenant', 'created_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Set tenant and created_by from context
        request = self.context.get('request')
        validated_data['tenant'] = request.user.tenant
        validated_data['created_by'] = request.user
        return super().create(validated_data)


class ConfigVersionSerializer(serializers.ModelSerializer):
    updated_by = UserSerializer(read_only=True)

    class Meta:
        model = ConfigVersion
        fields = [
            'id', 'config_object', 'environment', 'version_number',
            'value_snapshot', 'change_summary', 'updated_by', 'updated_at'
        ]
        read_only_fields = ['id', 'version_number', 'updated_by', 'updated_at']
