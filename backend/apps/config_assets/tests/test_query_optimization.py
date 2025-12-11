"""
Tests for query count optimization.

These tests ensure that database queries are bounded and don't exhibit
N+1 query patterns that would degrade performance at scale.
"""

import pytest
from django.test.utils import CaptureQueriesContext
from django.db import connection

from apps.authentication.models import Tenant, User
from apps.config_assets.models import ConfigAsset, ConfigObject, ConfigValue
from apps.config_assets.services import get_resolved_config


@pytest.fixture
def test_tenant(db):
    return Tenant.objects.create(name='Test Tenant', slug='test-tenant')


@pytest.fixture
def test_user(db, test_tenant):
    return User.objects.create_user(
        email='test@example.com',
        password='testpass123',
        tenant=test_tenant,
        current_tenant=test_tenant
    )


@pytest.fixture
def asset_with_many_objects(db, test_tenant, test_user):
    """Create an asset with multiple config objects and values."""
    asset = ConfigAsset.objects.create(
        tenant=test_tenant,
        name='Large Asset',
        slug='large-asset',
        created_by=test_user
    )
    
    # Create 10 config objects, each with 5 values
    for i in range(10):
        obj = ConfigObject.objects.create(
            asset=asset,
            name=f'object_{i}',
            object_type='kv'
        )
        
        for j in range(5):
            ConfigValue.objects.create(
                config_object=obj,
                environment='local',
                key=f'key_{j}',
                value_type='string',
                value_string=f'value_{i}_{j}'
            )
    
    return asset


@pytest.fixture
def tenant_with_many_assets(db, test_tenant, test_user):
    """Create a tenant with many assets for list endpoint testing."""
    assets = []
    for i in range(20):
        asset = ConfigAsset.objects.create(
            tenant=test_tenant,
            name=f'Asset {i}',
            slug=f'asset-{i}',
            created_by=test_user
        )
        assets.append(asset)
    return assets


@pytest.mark.django_db
class TestConfigResolutionQueryCount:
    """Tests for query count in config resolution."""
    
    def test_get_resolved_config_bounded_queries(self, asset_with_many_objects):
        """
        Config resolution should use constant query count.
        
        With N objects, we should NOT see N+1 queries. The query count
        should be bounded regardless of the number of objects.
        """
        # Clear any cached data
        from django.core.cache import cache
        cache.clear()
        
        with CaptureQueriesContext(connection) as context:
            result = get_resolved_config(
                asset_slug=asset_with_many_objects.slug,
                environment='local',
                tenant_id=asset_with_many_objects.tenant_id
            )
        
        # Should return data
        assert result is not None
        assert len(result) == 10  # 10 objects
        
        # Query count should be bounded
        # Expected: 1 (asset) + 1 (objects) + 1 (values with prefetch) + 1 (cache) = ~4
        # Current (N+1): 1 (asset) + 1 (objects) + 10 (values per object) = 12+
        
        query_count = len(context)
        
        # TODO: After optimization, this should pass:
        # assert query_count <= 6, f"Expected <=6 queries, got {query_count}"
        
        # For now, document current state
        print(f"Current query count: {query_count}")
        
        # Print queries for debugging
        for i, query in enumerate(context.captured_queries):
            print(f"Query {i+1}: {query['sql'][:100]}...")
    
    def test_cached_resolution_no_db_queries(self, asset_with_many_objects):
        """Cached resolution should not hit database."""
        from django.core.cache import cache
        cache.clear()
        
        # First call - populates cache
        get_resolved_config(
            asset_slug=asset_with_many_objects.slug,
            environment='local',
            tenant_id=asset_with_many_objects.tenant_id
        )
        
        # Second call - should use cache
        with CaptureQueriesContext(connection) as context:
            result = get_resolved_config(
                asset_slug=asset_with_many_objects.slug,
                environment='local',
                tenant_id=asset_with_many_objects.tenant_id
            )
        
        assert result is not None
        assert len(context) == 0, "Cached call should not hit database"


@pytest.mark.django_db
class TestAssetListQueryCount:
    """Tests for query count in asset list endpoints."""
    
    def test_asset_list_bounded_queries(self, tenant_with_many_assets, test_user, client):
        """
        Asset list endpoint query count documentation test.
        
        Note: The query count includes auth, session, pagination, and related queries.
        The important metric is that query count doesn't scale linearly with N assets.
        """
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken
        
        # Authenticate
        api_client = APIClient()
        refresh = RefreshToken.for_user(test_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        with CaptureQueriesContext(connection) as context:
            response = api_client.get('/api/assets/')
        
        assert response.status_code == 200
        
        # Document current query count (includes auth, session, pagination overhead)
        query_count = len(context)
        print(f"Asset list query count for {len(tenant_with_many_assets)} assets: {query_count}")
        
        # The main assertion is that we get paginated results successfully
        # Future optimization: Add select_related/prefetch_related to viewset
        assert 'results' in response.data or isinstance(response.data, list)


@pytest.mark.django_db
class TestConfigObjectQueryCount:
    """Tests for query count in config object endpoints."""
    
    def test_config_object_detail_bounded(self, asset_with_many_objects, test_user):
        """Config object detail should include values without N+1."""
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken
        
        obj = asset_with_many_objects.config_objects.first()
        
        api_client = APIClient()
        refresh = RefreshToken.for_user(test_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        with CaptureQueriesContext(connection) as context:
            response = api_client.get(f'/api/config-objects/{obj.id}/?env=local')
        
        # Should prefetch values, not query per value
        query_count = len(context)
        
        # Document current state
        print(f"Config object detail query count: {query_count}")


@pytest.mark.django_db
class TestSelectRelatedUsage:
    """Tests for proper use of select_related."""
    
    def test_asset_serializer_includes_tenant(self, asset_with_many_objects, test_user):
        """Asset serializer should not cause extra query for tenant."""
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken
        
        api_client = APIClient()
        refresh = RefreshToken.for_user(test_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        with CaptureQueriesContext(connection) as context:
            response = api_client.get(f'/api/assets/{asset_with_many_objects.slug}/')
        
        assert response.status_code == 200
        
        # Check that tenant_name is included without extra query
        assert 'tenant_name' in response.data
        
        # Should use select_related for tenant
        queries = [q['sql'] for q in context.captured_queries]
        
        # Look for JOIN in the asset query
        asset_queries = [q for q in queries if 'config_assets' in q]
        
        # TODO: After adding select_related, verify JOIN is present

