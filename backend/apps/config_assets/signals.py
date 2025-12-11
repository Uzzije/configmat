import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import ConfigValue, ConfigObject

logger = logging.getLogger(__name__)


@receiver([post_save, post_delete], sender=ConfigValue)
def invalidate_value_cache(sender, instance, **kwargs):
    """
    Invalidate cache when a ConfigValue changes.
    
    Cache keys invalidated:
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
        
        logger.debug(
            "Cache invalidated for config value change",
            extra={
                'tenant_slug': tenant.slug,
                'asset_slug': asset.slug,
                'config_object': config_object.name,
                'key': instance.key,
                'environment': env
            }
        )
        
    except Exception as e:
        # Don't block save on cache error, but log it
        logger.error(
            f"Cache invalidation error for ConfigValue: {e}",
            exc_info=True,
            extra={
                'config_value_id': str(instance.id) if instance.id else 'new',
                'error': str(e)
            }
        )


@receiver([post_save, post_delete], sender=ConfigObject)
def invalidate_object_cache(sender, instance, **kwargs):
    """
    Invalidate asset cache when an Object changes (e.g. name change or delete).
    
    Note: Invalidates all environments since we can't efficiently determine
    which environments have values for this object without additional queries.
    """
    try:
        asset = instance.asset
        tenant = asset.tenant
        
        # Invalidate all known environments
        # Note: For production with many environments, consider tracking
        # active environments in the tenant model
        envs = ['local', 'stage', 'prod', 'production']
        invalidated_keys = []
        
        for env in envs:
            key = f"config:{tenant.slug}:{asset.slug}:{env}"
            cache.delete(key)
            invalidated_keys.append(key)
        
        logger.debug(
            "Cache invalidated for config object change",
            extra={
                'tenant_slug': tenant.slug,
                'asset_slug': asset.slug,
                'config_object': instance.name,
                'invalidated_keys': invalidated_keys
            }
        )
             
    except Exception as e:
        # Don't block save on cache error, but log it
        logger.error(
            f"Cache invalidation error for ConfigObject: {e}",
            exc_info=True,
            extra={
                'config_object_id': str(instance.id) if instance.id else 'new',
                'error': str(e)
            }
        )
