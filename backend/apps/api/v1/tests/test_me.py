"""
Tests for API key metadata endpoint.
"""

import pytest
from rest_framework.test import APIClient
from rest_framework import status


@pytest.mark.django_db
class TestAPIKeyMetadataView:
    """Test cases for API key metadata endpoint."""
    
    def test_get_metadata_success(self, test_api_key):
        """Test getting API key metadata successfully."""
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=test_api_key.key_value)
        
        response = client.get('/api/v1/me/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['organization'] == 'test-org'
        assert response.data['environment'] == 'local'
        assert response.data['scope'] == 'tenant'
        assert response.data['label'] == 'Test API Key'
        assert 'asset' not in response.data  # Tenant-scoped, no asset
    
    def test_get_metadata_production_key(self, production_api_key):
        """Test metadata for production-scoped key."""
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=production_api_key.key_value)
        
        response = client.get('/api/v1/me/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['organization'] == 'test-org'
        assert response.data['environment'] == 'production'
        assert response.data['scope'] == 'tenant'
    
    def test_get_metadata_no_auth(self):
        """Test 403 when no API key provided."""
        client = APIClient()
        
        response = client.get('/api/v1/me/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_get_metadata_invalid_key(self):
        """Test 403 when invalid API key provided."""
        client = APIClient()
        client.credentials(HTTP_X_API_KEY='invalid_key')
        
        response = client.get('/api/v1/me/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_get_metadata_response_structure(self, test_api_key):
        """Test response has correct structure."""
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=test_api_key.key_value)
        
        response = client.get('/api/v1/me/')
        
        assert response.status_code == status.HTTP_200_OK
        
        # Check required fields
        required_fields = ['organization', 'environment', 'scope', 'label']
        for field in required_fields:
            assert field in response.data, f"Missing field: {field}"
