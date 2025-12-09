from django.test import TestCase
from django.core.cache import cache
from unittest.mock import patch
from apps.authentication.models import Tenant
from apps.config_assets.models import ConfigAsset, ConfigObject, ConfigValue

class CachingTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='Cache Tenant', slug='cache-tenant')
        self.asset = ConfigAsset.objects.create(tenant=self.tenant, name='Cache Asset', slug='cache-asset')
        self.object = ConfigObject.objects.create(asset=self.asset, name='Cache Object', object_type='kv')
        self.value = ConfigValue.objects.create(
            config_object=self.object,
            key='cache_key',
            environment='local',
            value_string='initial'
        )
        self.cache_key = f"config:{self.tenant.slug}:{self.asset.slug}:local"
        
        # Clear cache
        cache.clear()

    def test_cache_invalidation_on_update(self):
        # 1. Update value, should invalidate asset cache
        # Set a dummy value in cache first to simulate checking
        cache.set(self.cache_key, {'foo': 'bar'})
        self.assertIsNotNone(cache.get(self.cache_key))
        
        # Save
        self.value.value_string = 'updated'
        self.value.save()
        
        # Check cache is cleared
        self.assertIsNone(cache.get(self.cache_key))

    def test_cache_invalidation_on_delete(self):
        cache.set(self.cache_key, {'foo': 'bar'})
        
        self.value.delete()
        self.assertIsNone(cache.get(self.cache_key))
