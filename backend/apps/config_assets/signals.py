from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import ConfigValue, ConfigObject, ConfigAsset

@receiver([post_save, post_delete], sender=ConfigValue)
def invalidate_value_cache(sender, instance, **kwargs):
    """
    Invalidate cache when a ConfigValue changes.
    Cache keys: 
    1. config:{tenant}:{asset}:{env} (Full asset values)
    2. config:{tenant}:{asset}:{object}:{key}:{env} (Specific value)
    """
    try:
        config_object = instance.config_object
        asset = config_object.asset
        tenant = asset.tenant
        env = instance.environment
        
        # Pattern 1: Full Asset
        key1 = f"config:{tenant.slug}:{asset.slug}:{env}"
        cache.delete(key1)
        
        # Pattern 2: Specific Value
        key2 = f"config:{tenant.slug}:{asset.slug}:{config_object.name}:{instance.key}:{env}"
        cache.delete(key2)
        
    except Exception as e:
        # Don't block save on cache error
        print(f"Cache invalidation error: {e}")

@receiver([post_save, post_delete], sender=ConfigObject)
def invalidate_object_cache(sender, instance, **kwargs):
    """
    Invalidate asset cache when an Object changes (e.g. name change or delete)
    """
    try:
        asset = instance.asset
        tenant = asset.tenant
        
        # We don't know environment here efficiently without querying values.
        # But we can invalidate keys for all environments if we track them, 
        # or we accept that object structure changes invalidate the asset view.
        # Since keys include environment, we typically need to iterate or wildcard delete.
        # Django default cache backend doesn't support wildcard delete efficiently.
        # For High Availability, we might use Redis keys pattern delete, but that's slow.
        # Best effort: Invalidate 'local', 'stage', 'prod'.
        
        envs = ['local', 'stage', 'prod']
        for env in envs:
             key = f"config:{tenant.slug}:{asset.slug}:{env}"
             cache.delete(key)
             
    except Exception:
        pass
