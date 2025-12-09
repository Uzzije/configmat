"""
Tests for assets endpoints.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status


@pytest.mark.django_db
class TestAssetListView:
    """Test cases for asset list endpoint."""
    
    def test_list_assets_success(
        self,
        test_api_key,
        multiple_assets
    ):
        """Test listing assets successfully."""
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=test_api_key.key_value)
        
        response = client.get('/api/v1/assets/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'assets' in response.data
        assert len(response.data['assets']) == 3
        
        # Check structure
        asset = response.data['assets'][0]
        assert 'id' in asset
        assert 'slug' in asset
        assert 'name' in asset
        assert 'description' in asset
    
    def test_list_assets_empty(
        self,
        test_api_key,
        test_tenant
    ):
        """Test listing when no assets exist."""
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=test_api_key.key_value)
        
        response = client.get('/api/v1/assets/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'assets' in response.data
        assert len(response.data['assets']) == 0
    
    def test_list_assets_no_auth(self):
        """Test 403 when no API key provided."""
        client = APIClient()
        
        response = client.get('/api/v1/assets/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    # test_list_assets_org_not_found removed - org is now derived from API key
    
    def test_list_assets_wrong_tenant(
        self,
        test_api_key,
        other_tenant
    ):
        """Test that wrong tenant returns empty list (assets filtered by tenant)."""
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=test_api_key.key_value)
        
        # API key's tenant has no assets, so should return empty list
        response = client.get('/api/v1/assets/')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['assets']) == 0
    
    def test_list_assets_ordered_by_name(
        self,
        test_api_key,
        test_tenant,
        test_user
    ):
        """Test that assets are ordered by name."""
        from apps.config_assets.models import ConfigAsset
        
        # Create assets in random order
        ConfigAsset.objects.create(
            tenant=test_tenant,
            slug='zebra',
            name='Zebra Asset',
            created_by=test_user
        )
        ConfigAsset.objects.create(
            tenant=test_tenant,
            slug='alpha',
            name='Alpha Asset',
            created_by=test_user
        )
        ConfigAsset.objects.create(
            tenant=test_tenant,
            slug='beta',
            name='Beta Asset',
            created_by=test_user
        )
        
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=test_api_key.key_value)
        
        response = client.get('/api/v1/assets/')
        
        assert response.status_code == status.HTTP_200_OK
        names = [asset['name'] for asset in response.data['assets']]
        assert names == ['Alpha Asset', 'Beta Asset', 'Zebra Asset']


@pytest.mark.django_db
class TestAssetDetailView:
    """Test cases for asset detail endpoint."""
    
    def test_get_asset_success(
        self,
        test_api_key,
        test_asset,
        test_config_object
    ):
        """Test getting asset details successfully."""
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=test_api_key.key_value)
        
        response = client.get(
            '/api/v1/assets/test-asset/'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['slug'] == 'test-asset'
        assert response.data['name'] == 'Test Asset'
        assert 'objects' in response.data
        assert len(response.data['objects']) == 1
        assert response.data['objects'][0]['name'] == 'app_settings'
    
    def test_get_asset_not_found(
        self,
        test_api_key,
        test_tenant
    ):
        """Test 404 when asset doesn't exist."""
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=test_api_key.key_value)
        
        response = client.get(
            '/api/v1/assets/nonexistent/'
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'error' in response.data
    
    def test_get_asset_no_auth(self, test_asset):
        """Test 403 when no API key provided."""
        client = APIClient()
        
        response = client.get(
            '/api/v1/assets/test-asset/'
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_get_asset_wrong_tenant(
        self,
        test_api_key,
        other_tenant,
        test_user
    ):
        """Test 403 when accessing asset from different tenant."""
        from apps.config_assets.models import ConfigAsset
        
        # Create asset in other tenant
        ConfigAsset.objects.create(
            tenant=other_tenant,
            slug='other-asset',
            name='Other Asset',
            created_by=test_user
        )
        
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=test_api_key.key_value)
        
        response = client.get(
            '/api/v1/assets/other-asset/'
        )
        
        # Asset not found in this tenant returns 404 (not 403)
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_get_asset_with_multiple_objects(
        self,
        test_api_key,
        test_asset
    ):
        """Test getting asset with multiple config objects."""
        from apps.config_assets.models import ConfigObject
        
        # Create multiple config objects
        ConfigObject.objects.create(
            asset=test_asset,
            name='database',
            object_type='kv'
        )
        ConfigObject.objects.create(
            asset=test_asset,
            name='stripe',
            object_type='kv'
        )
        
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=test_api_key.key_value)
        
        response = client.get(
            '/api/v1/assets/test-asset/'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['objects']) == 2
        
        # Check objects are ordered by name
        names = [obj['name'] for obj in response.data['objects']]
        assert names == ['database', 'stripe']
    
    def test_get_asset_response_structure(
        self,
        test_api_key,
        test_asset,
        test_config_object
    ):
        """Test asset response has correct structure."""
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=test_api_key.key_value)
        
        response = client.get(
            '/api/v1/assets/test-asset/'
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Check asset fields
        required_fields = ['id', 'slug', 'name', 'description', 'objects']
        for field in required_fields:
            assert field in response.data
        
        # Check object fields
        obj = response.data['objects'][0]
        object_fields = ['id', 'name', 'type', 'description']
        for field in object_fields:
            assert field in obj
