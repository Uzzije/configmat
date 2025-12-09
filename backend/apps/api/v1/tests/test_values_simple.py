import pytest
from rest_framework import status
from rest_framework.test import APIClient

@pytest.mark.django_db
class TestConfigValuesView:
    
    def test_get_values_unauthenticated(self):
        """Test that unauthenticated requests are rejected."""
        client = APIClient()
        response = client.get("/api/v1/assets/test-asset/values/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_values_success(self, test_api_key, test_asset, test_config_values):
        """Test retrieving values with a valid API key."""
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=test_api_key.key_value)
        
        url = f"/api/v1/assets/{test_asset.slug}/values/"
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify structure: {"object_name": {"key": "value"}}
        assert 'app_settings' in data
        settings = data['app_settings']
        assert settings['retries'] == '3'
        assert settings['theme'] == 'dark'
        assert settings['timeout'] == '30'

    def test_get_values_scope_enforcement(self, production_api_key, test_asset, test_config_values, production_config_values):
        """
        Ensure production API key retrieves production values, 
        ignoring 'environment=local' query parameter.
        """
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=production_api_key.key_value)
        
        # Request 'local' explicitly, but key is 'production' scoped
        url = f"/api/v1/assets/{test_asset.slug}/values/?environment=local"
        response = client.get(url)
        
        # Should fail with 403 because we requested 'local' but allowed only 'production'
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_values_asset_not_found(self, test_api_key):
        """Test 404 for non-existent asset."""
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=test_api_key.key_value)
        
        response = client.get("/api/v1/assets/non-existent-asset/values/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.django_db
class TestConfigValueDetailView:
    
    def test_get_detail_value_success(self, test_api_key, test_asset, test_config_values):
        """Test getting a single configuration value."""
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=test_api_key.key_value)
        
        url = f"/api/v1/assets/{test_asset.slug}/objects/app_settings/values/theme/"
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data['key'] == 'theme'
        assert data['value'] == 'dark'
        assert data['object'] == 'app_settings'
        assert data['environment'] == 'local'

    def test_get_detail_value_not_found(self, test_api_key, test_asset):
        """Test getting a non-existent key."""
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=test_api_key.key_value)
        
        url = f"/api/v1/assets/{test_asset.slug}/objects/app_settings/values/non_existent_key/"
        response = client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
