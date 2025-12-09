"""
Tests for granular config value endpoint.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.core.cache import cache


@pytest.mark.django_db
class TestConfigValueDetailView:
    """Test cases for granular config value endpoint."""
    
    def setup_method(self):
        """Clear cache before each test."""
        cache.clear()
    
    def test_get_specific_value_success(
        self,
        test_api_key,
        test_asset,
        test_config_object,
        test_config_values
    ):
        """Test getting a specific config value successfully."""
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=test_api_key.key_value)
        
        response = client.get(
            '/api/v1/assets/test-asset/objects/app_settings/values/retries/',
            {'environment': 'local'}
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['key'] == 'retries'
        assert response.data['value'] == '3'
        assert response.data['type'] == 'string'
        assert response.data['object'] == 'app_settings'
        assert response.data['environment'] == 'local'
    
    def test_get_specific_value_default_environment(
        self,
        test_api_key,
        test_asset,
        test_config_object,
        test_config_values
    ):
        """Test that 'local' is the default environment."""
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=test_api_key.key_value)
        
        # Don't specify environment
        response = client.get(
            '/api/v1/assets/test-asset/objects/app_settings/values/theme/'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['value'] == 'dark'
        assert response.data['environment'] == 'local'
    
    def test_get_specific_value_json_type(
        self,
        test_api_key,
        test_asset,
        test_config_object
    ):
        """Test getting JSON type value."""
        from apps.config_assets.models import ConfigValue
        
        # Create JSON value
        ConfigValue.objects.create(
            config_object=test_config_object,
            environment='local',
            key='database_config',
            value_type='json',
            value_json={'host': 'localhost', 'port': 5432}
        )
        
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=test_api_key.key_value)
        
        response = client.get(
            '/api/v1/assets/test-asset/objects/app_settings/values/database_config/',
            {'environment': 'local'}
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['key'] == 'database_config'
        assert response.data['value'] == {'host': 'localhost', 'port': 5432}
        assert response.data['type'] == 'json'
    
    # test_get_specific_value_org_not_found removed - org is now derived from API key
    
    def test_get_specific_value_asset_not_found(
        self,
        test_api_key,
        test_tenant
    ):
        """Test 404 when asset doesn't exist."""
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=test_api_key.key_value)
        
        response = client.get(
            '/api/v1/assets/nonexistent/objects/app_settings/values/retries/'
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'error' in response.data
    
    def test_get_specific_value_object_not_found(
        self,
        test_api_key,
        test_asset
    ):
        """Test 404 when config object doesn't exist."""
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=test_api_key.key_value)
        
        response = client.get(
            '/api/v1/assets/test-asset/objects/nonexistent/values/retries/'
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'error' in response.data
        assert 'nonexistent' in response.data['error']
    
    def test_get_specific_value_key_not_found(
        self,
        test_api_key,
        test_asset,
        test_config_object,
        test_config_values
    ):
        """Test 404 when key doesn't exist."""
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=test_api_key.key_value)
        
        response = client.get(
            '/api/v1/assets/test-asset/objects/app_settings/values/nonexistent_key/'
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'error' in response.data
        assert 'nonexistent_key' in response.data['error']
    
    def test_get_specific_value_wrong_environment(
        self,
        test_api_key,
        test_asset,
        test_config_object,
        test_config_values
    ):
        """Test 403 when key doesn't exist in specified environment or API key scope prevents access."""
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=test_api_key.key_value)
        
        # Try to get local value from production environment
        response = client.get(
            '/api/v1/assets/test-asset/objects/app_settings/values/retries/',
            {'environment': 'production'}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'error' in response.data
        assert 'production' in response.data['error']
    
    def test_get_specific_value_wrong_tenant(
        self,
        test_api_key,
        other_tenant,
        test_user
    ):
        """Test 403 when API key doesn't have access to tenant."""
        from apps.config_assets.models import ConfigAsset, ConfigObject, ConfigValue
        
        # Create asset in other tenant
        other_asset = ConfigAsset.objects.create(
            tenant=other_tenant,
            slug='other-asset',
            name='Other Asset',
            created_by=test_user
        )
        
        other_obj = ConfigObject.objects.create(
            asset=other_asset,
            name='settings',
            object_type='kv'
        )
        
        ConfigValue.objects.create(
            config_object=other_obj,
            environment='local',
            key='test',
            value_type='string',
            value_string='value'
        )
        
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=test_api_key.key_value)
        
        response = client.get(
            '/api/v1/assets/other-asset/objects/settings/values/test/'
        )
        
        # Asset not found in this tenant returns 404 (not 403)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'error' in response.data
    
    def test_get_specific_value_environment_scope(
        self,
        production_api_key,
        test_asset,
        test_config_object,
        test_config_values
    ):
        """Test 403 when API key is scoped to different environment."""
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=production_api_key.key_value)
        
        # Try to access 'local' environment with production-scoped key
        response = client.get(
            '/api/v1/assets/test-asset/objects/app_settings/values/retries/',
            {'environment': 'local'}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'error' in response.data
        assert 'environment' in response.data['error'].lower()
    
    def test_get_specific_value_no_auth(self, test_asset):
        """Test 403 when no API key provided."""
        client = APIClient()
        # No credentials
        
        response = client.get(
            '/api/v1/assets/test-asset/objects/app_settings/values/retries/'
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_get_specific_value_invalid_api_key(self, test_asset):
        """Test 403 when invalid API key provided."""
        client = APIClient()
        client.credentials(HTTP_X_API_KEY='invalid_key')
        
        response = client.get(
            '/api/v1/assets/test-asset/objects/app_settings/values/retries/'
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_get_specific_value_caching(
        self,
        test_api_key,
        test_asset,
        test_config_object,
        test_config_values
    ):
        """Test that responses are cached."""
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=test_api_key.key_value)
        
        # First request
        response1 = client.get(
            '/api/v1/assets/test-asset/objects/app_settings/values/retries/',
            {'environment': 'local'}
        )
        
        # Check cache
        cache_key = 'config:test-org:test-asset:app_settings:retries:local'
        cached_data = cache.get(cache_key)
        assert cached_data is not None
        assert cached_data['value'] == '3'
        
        # Second request should hit cache
        response2 = client.get(
            '/api/v1/assets/test-asset/objects/app_settings/values/retries/',
            {'environment': 'local'}
        )
        
        assert response1.data == response2.data
    
    def test_get_specific_value_response_structure(
        self,
        test_api_key,
        test_asset,
        test_config_object,
        test_config_values
    ):
        """Test response has correct structure."""
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=test_api_key.key_value)
        
        response = client.get(
            '/api/v1/assets/test-asset/objects/app_settings/values/timeout/',
            {'environment': 'local'}
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Check all required fields are present
        required_fields = ['key', 'value', 'type', 'object', 'environment']
        for field in required_fields:
            assert field in response.data, f"Missing field: {field}"
        
        # Verify field values
        assert response.data['key'] == 'timeout'
        assert response.data['value'] == '30'
        assert response.data['type'] == 'string'
        assert response.data['object'] == 'app_settings'
        assert response.data['environment'] == 'local'
