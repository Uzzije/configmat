import pytest
from apps.authentication.models import User, Tenant
from apps.config_assets.models import ConfigAsset, ConfigObject, ConfigValue
import secrets

@pytest.fixture
def test_tenant(db):
    return Tenant.objects.create(name='Test Org', slug='test-org')

@pytest.fixture
def test_user(db, test_tenant):
    return User.objects.create_user(
        email='user@test.com',
        password='password',
        tenant=test_tenant
    )

@pytest.fixture
def test_asset(db, test_tenant, test_user):
    return ConfigAsset.objects.create(
        tenant=test_tenant,
        slug='test-asset',
        name='Test Asset',
        created_by=test_user
    )

@pytest.fixture
def test_config_object(db, test_asset):
    return ConfigObject.objects.create(
        asset=test_asset,
        name='app_settings',
        object_type='kv'
    )

@pytest.fixture
def test_config_values_local(db, test_config_object):
    """Seed local values"""
    v1 = ConfigValue.objects.create(config_object=test_config_object, environment='local', key='host', value_type='string', value_string='localhost')
    v2 = ConfigValue.objects.create(config_object=test_config_object, environment='local', key='debug', value_type='boolean', value_string='true')
    return [v1, v2]
