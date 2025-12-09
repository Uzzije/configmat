"""
Test fixtures for Public API v1 tests.
"""

import pytest
from apps.authentication.models import User, Tenant
from apps.config_assets.models import ConfigAsset, ConfigObject, ConfigValue
from apps.api_keys.models import APIKey
import secrets


@pytest.fixture
def test_tenant(db):
    """Create a test tenant."""
    return Tenant.objects.create(
        name='Test Organization',
        slug='test-org'
    )


@pytest.fixture
def other_tenant(db):
    """Create another tenant for access control tests."""
    return Tenant.objects.create(
        name='Other Organization',
        slug='other-org'
    )


@pytest.fixture
def test_user(db, test_tenant):
    """Create a test user."""
    return User.objects.create_user(
        email='test@example.com',
        password='testpass123',
        tenant=test_tenant
    )


@pytest.fixture
def test_api_key(db, test_tenant, test_user):
    """Create a test API key."""
    # Generate a real API key
    key_value = f"cm_{secrets.token_urlsafe(32)}"
    
    # Hash the key
    key_hash = APIKey.hash_key(key_value)
    
    api_key = APIKey.objects.create(
        tenant=test_tenant,
        scope='tenant',
        environment='local',
        created_by=test_user,
        label='Test API Key',
        key_hash=key_hash,
        key_prefix=key_value[:16]  # First 16 chars for lookup
    )
    
    # Attach the raw key value for testing
    api_key.key_value = key_value
    return api_key


@pytest.fixture
def production_api_key(db, test_tenant, test_user):
    """Create an API key scoped to production environment."""
    key_value = f"cm_{secrets.token_urlsafe(32)}"
    key_hash = APIKey.hash_key(key_value)
    
    api_key = APIKey.objects.create(
        tenant=test_tenant,
        scope='tenant',
        environment='production',
        created_by=test_user,
        label='Production API Key',
        key_hash=key_hash,
        key_prefix=key_value[:16]  # First 16 chars for lookup
    )
    
    api_key.key_value = key_value
    return api_key


@pytest.fixture
def test_asset(db, test_tenant, test_user):
    """Create a test asset."""
    return ConfigAsset.objects.create(
        tenant=test_tenant,
        slug='test-asset',
        name='Test Asset',
        description='Test asset for API testing',
        created_by=test_user
    )


@pytest.fixture
def test_config_object(db, test_asset):
    """Create a test config object."""
    return ConfigObject.objects.create(
        asset=test_asset,
        name='app_settings',
        object_type='kv',
        description='Application settings'
    )


@pytest.fixture
def test_config_values(db, test_config_object):
    """Create test config values."""
    values = [
        ConfigValue.objects.create(
            config_object=test_config_object,
            environment='local',
            key='retries',
            value_type='string',
            value_string='3'
        ),
        ConfigValue.objects.create(
            config_object=test_config_object,
            environment='local',
            key='theme',
            value_type='string',
            value_string='dark'
        ),
        ConfigValue.objects.create(
            config_object=test_config_object,
            environment='local',
            key='timeout',
            value_type='string',
            value_string='30'
        ),
    ]
    return values


@pytest.fixture
def production_config_values(db, test_config_object):
    """Create production config values."""
    values = [
        ConfigValue.objects.create(
            config_object=test_config_object,
            environment='production',
            key='retries',
            value_type='string',
            value_string='5'
        ),
        ConfigValue.objects.create(
            config_object=test_config_object,
            environment='production',
            key='theme',
            value_type='string',
            value_string='light'
        ),
    ]
    return values


@pytest.fixture
def multiple_assets(db, test_tenant, test_user):
    """Create multiple test assets."""
    assets = []
    for i in range(3):
        asset = ConfigAsset.objects.create(
            tenant=test_tenant,
            slug=f'asset-{i}',
            name=f'Asset {i}',
            description=f'Test asset {i}',
            created_by=test_user
        )
        assets.append(asset)
    return assets
