import pytest
from django.core.cache import cache
from apps.config_assets.services import (
    get_resolved_config,
    invalidate_config_cache,
    create_config_version,
    promote_asset,
    rollback_to_version
)
from apps.config_assets.models import ConfigValue, ConfigObject

@pytest.mark.django_db
class TestConfigServices:
    
    def test_get_resolved_config_success(self, test_asset, test_config_object, test_config_values_local):
        """Test fetching configuration and caching mechanism."""
        # 1. First call (Uncached)
        config = get_resolved_config(test_asset.slug, 'local', test_asset.tenant.id)
        assert config is not None
        assert 'app_settings' in config
        assert config['app_settings']['host'] == 'localhost'
        assert config['app_settings']['debug'] is True
        
        # 2. Verify Cache populated
        cached = cache.get(f"config:{test_asset.tenant.id}:local:{test_asset.slug}")
        assert cached == config
        
        # 3. Modify DB directly
        ConfigValue.objects.filter(key='host').update(value_string='hacked')
        
        # 4. Second call (Cached) - should return old value
        config_2 = get_resolved_config(test_asset.slug, 'local', test_asset.tenant.id)
        assert config_2['app_settings']['host'] == 'localhost'
        
        # 5. Invalidate and check update
        invalidate_config_cache(test_asset.id, 'local')
        config_3 = get_resolved_config(test_asset.slug, 'local', test_asset.tenant.id)
        assert config_3['app_settings']['host'] == 'hacked'

    def test_promote_asset_kv_logic(self, test_asset, test_config_object, test_config_values_local, test_user):
        """
        Test promotion logic for KV objects (Structure Sync).
        """
        # Setup Target (Production)
        # Prod has its own values for 'host', misses 'debug', has extra 'extra'
        ConfigValue.objects.create(config_object=test_config_object, environment='production', key='host', value_type='string', value_string='prod-db')
        ConfigValue.objects.create(config_object=test_config_object, environment='production', key='extra', value_type='string', value_string='delete-me')
        
        # Action
        success = promote_asset(test_asset.id, 'local', 'production', test_user.id)
        assert success is True
        
        # Verification
        prod_values = ConfigValue.objects.filter(config_object=test_config_object, environment='production')
        prod_map = {v.key: v.value_string for v in prod_values}
        
        # Logic Check
        assert prod_map.get('host') == 'prod-db'  # Preserved existing value
        assert prod_map.get('debug') == 'true'    # Copied missing key/value from source
        assert 'extra' not in prod_map            # Removed obsolete key

    def test_promote_asset_json_logic(self, test_asset, test_user):
        """
        Test promotion logic for JSON objects (Full Overwrite).
        """
        obj = ConfigObject.objects.create(asset=test_asset, name='features', object_type='json')
        
        # Source
        ConfigValue.objects.create(
            config_object=obj, environment='local', key='features', 
            value_type='json', value_json={'f1': True}
        )
        # Target
        ConfigValue.objects.create(
             config_object=obj, environment='production', key='features',
             value_type='json', value_json={'f1': False, 'old': True}
        )
        
        success = promote_asset(test_asset.id, 'local', 'production', test_user.id)
        assert success is True
        
        val = ConfigValue.objects.get(config_object=obj, environment='production')
        assert val.value_json == {'f1': True}  # Fully overwritten

    def test_rollback_to_version(self, test_config_object, test_config_values_local, test_user):
        """Test rolling back to a previous version."""
        # 1. Create v1 snapshot
        v1 = create_config_version(test_config_object, 'local', test_user.id, "v1")
        
        # 2. Modify state: Modify 'host', Delete 'debug', Add 'new'
        ConfigValue.objects.filter(config_object=test_config_object, key='host').update(value_string='modified')
        ConfigValue.objects.filter(config_object=test_config_object, key='debug').delete()
        ConfigValue.objects.create(
            config_object=test_config_object, environment='local', 
            key='new', value_type='string', value_string='v2-new'
        )
        
        # 3. Rollback
        success = rollback_to_version(v1.id, test_user.id)
        assert success is True
        
        # 4. Verify restoration
        values = ConfigValue.objects.filter(config_object=test_config_object, environment='local')
        v_map = {v.key: v.value_string for v in values}
        
        assert v_map.get('host') == 'localhost' # Restored original
        assert v_map.get('debug') == 'true'     # Resurrected
        assert 'new' not in v_map               # Pruned
