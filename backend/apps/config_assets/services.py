import logging
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Prefetch
from .models import ConfigAsset, ConfigObject, ConfigValue, ConfigVersion
from apps.audit.services import log_activity

logger = logging.getLogger(__name__)

CACHE_TTL = 300  # 5 minutes


def _resolve_value(val):
    """
    Resolve a ConfigValue to its Python representation.
    
    Args:
        val: ConfigValue instance
        
    Returns:
        The resolved value (str, float, bool, dict, or reference dict)
    """
    if val.value_type == 'string':
        return val.value_string
    elif val.value_type == 'number':
        try:
            return float(val.value_string)
        except (ValueError, TypeError):
            return 0
    elif val.value_type == 'boolean':
        return val.value_string == 'true'
    elif val.value_type == 'json':
        return val.value_json
    elif val.value_type == 'reference':
        return {"_ref": str(val.value_reference_id)}
    return None


def get_resolved_config(asset_slug, environment, tenant_id):
    """
    Resolve configuration for a given asset and environment.
    Returns a dictionary of {object_name: resolved_value}.
    
    Performance: Uses prefetch_related to avoid N+1 queries.
    """
    cache_key = f"config:{tenant_id}:{environment}:{asset_slug}"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return cached_data

    try:
        asset = ConfigAsset.objects.get(
            slug=asset_slug, 
            tenant_id=tenant_id
        )
    except ConfigAsset.DoesNotExist:
        return None

    # Fetch all objects with their values pre-fetched (avoids N+1 queries)
    config_objects = asset.config_objects.prefetch_related(
        Prefetch(
            'values',
            queryset=ConfigValue.objects.filter(environment=environment),
            to_attr='env_values'
        )
    ).all()
    
    resolved_config = {}
    
    for obj in config_objects:
        # Use prefetched values instead of querying per object
        values = obj.env_values  # Pre-fetched!
        
        if obj.object_type == 'kv':
            # Resolve KV object as a dictionary of keys
            kv_dict = {val.key: _resolve_value(val) for val in values}
            resolved_config[obj.name] = kv_dict
        else:
            # Non-KV (e.g. 'json' type), assume single value per environment
            value_obj = values[0] if values else None
            resolved_config[obj.name] = _resolve_value(value_obj) if value_obj else None

    # Cache the result
    cache.set(cache_key, resolved_config, CACHE_TTL)
    
    return resolved_config

def invalidate_config_cache(asset_id, environment):
    """Invalidate cache for a specific asset/env"""
    try:
        asset = ConfigAsset.objects.get(id=asset_id)
        cache_key = f"config:{asset.tenant_id}:{environment}:{asset.slug}"
        cache.delete(cache_key)
    except ConfigAsset.DoesNotExist:
        pass


def create_config_version(config_object, environment, user_id, change_summary=""):
    """Create a version snapshot for a config object in an environment"""
    values = config_object.values.filter(environment=environment)
    
    if not values.exists():
        return None
        
    value_snapshot = []
    for val in values:
        value_snapshot.append({
            'key': val.key,
            'value_type': val.value_type,
            'value_string': val.value_string,
            'value_json': val.value_json,
            'reference_id': str(val.value_reference_id) if val.value_reference_id else None
        })
    
    # Calculate next version number
    last_version = ConfigVersion.objects.filter(
        config_object=config_object, 
        environment=environment
    ).order_by('-version_number').first()
    
    next_version = (last_version.version_number + 1) if last_version else 1
    
    return ConfigVersion.objects.create(
        config_object=config_object,
        environment=environment,
        version_number=next_version,
        value_snapshot={'values': value_snapshot},
        updated_by_id=user_id,
        change_summary=change_summary
    )


@transaction.atomic
def promote_asset(asset_id, from_env, to_env, user_id):
    """
    Promote configuration from one environment to another.
    
    For KV objects: Syncs structure (keys). Adds new keys, removes obsolete keys. Preserves existing values.
    For other types: Overwrites target with source (since structure/data are inseparable).
    
    Transaction Safety: This operation is atomic - all changes succeed or all are rolled back.
    """
    try:
        # Lock the asset row to prevent concurrent modifications
        asset = ConfigAsset.objects.select_for_update().get(id=asset_id)
    except ConfigAsset.DoesNotExist:
        logger.warning(f"Promote failed: asset {asset_id} not found")
        return False

    logger.info(
        f"Promoting asset {asset.slug} from {from_env} to {to_env}",
        extra={
            'asset_id': str(asset_id),
            'from_env': from_env,
            'to_env': to_env,
            'user_id': str(user_id)
        }
    )

    # Get all objects for this asset
    config_objects = asset.config_objects.all()
    
    for obj in config_objects:
        # Get all source values
        source_values = obj.values.filter(environment=from_env)
        
        if not source_values.exists():
            # If source is empty, clear target
            obj.values.filter(environment=to_env).delete()
            continue

        if obj.object_type == 'kv':
            # --- KV Logic: Sync Keys, Preserve Values ---
            source_keys = {v.key: v for v in source_values}
            target_values = obj.values.filter(environment=to_env)
            target_keys = {v.key: v for v in target_values}
            
            # 1. Add missing keys (copy from source)
            for key, source_val in source_keys.items():
                if key not in target_keys:
                    ConfigValue.objects.create(
                        config_object=obj,
                        environment=to_env,
                        key=key,
                        value_type=source_val.value_type,
                        value_string=source_val.value_string,
                        value_json=source_val.value_json,
                        value_reference=source_val.value_reference
                    )
            
            # 2. Remove extra keys (not in source)
            keys_to_remove = set(target_keys.keys()) - set(source_keys.keys())
            if keys_to_remove:
                ConfigValue.objects.filter(
                    config_object=obj,
                    environment=to_env,
                    key__in=keys_to_remove
                ).delete()
                
            # 3. Existing keys are preserved (do nothing)

        else:
            # --- Non-KV Logic: Overwrite (Full Promote) ---
            # Clear target
            obj.values.filter(environment=to_env).delete()
            
            # Copy all from source
            for source_value in source_values:
                ConfigValue.objects.create(
                    config_object=obj,
                    environment=to_env,
                    key=source_value.key,
                    value_type=source_value.value_type,
                    value_string=source_value.value_string,
                    value_json=source_value.value_json,
                    value_reference=source_value.value_reference
                )
        
        # Create version snapshot for target env
        create_config_version(
            config_object=obj,
            environment=to_env,
            user_id=user_id,
            change_summary=f"Promoted from {from_env} (Structure Sync)"
        )
    
    # Cache invalidation is done outside the transaction for safety
    # (cache failures should not cause DB rollback)
    transaction.on_commit(lambda: invalidate_config_cache(asset.id, to_env))
    
    # Log activity (also on commit to ensure DB state is consistent)
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
        transaction.on_commit(lambda: log_activity(
            user=user,
            action="Promoted Asset",
            target=f"{asset.name} ({from_env} -> {to_env})",
            details={
                "asset_slug": asset.slug,
                "from_env": from_env,
                "to_env": to_env
            }
        ))
    except User.DoesNotExist:
        logger.warning(f"User {user_id} not found for activity log")
    
    return True


@transaction.atomic
def rollback_to_version(version_id, user_id):
    """
    Rollback a config object to a specific version.
    
    Transaction Safety: This operation is atomic - all changes succeed or all are rolled back.
    """
    try:
        version = ConfigVersion.objects.select_related(
            'config_object', 'config_object__asset'
        ).get(id=version_id)
    except ConfigVersion.DoesNotExist:
        logger.warning(f"Rollback failed: version {version_id} not found")
        return False
        
    config_object = version.config_object
    environment = version.environment
    snapshot = version.value_snapshot
    values = snapshot.get('values', [])
    
    logger.info(
        f"Rolling back {config_object.name} to v{version.version_number}",
        extra={
            'config_object_id': str(config_object.id),
            'version_id': str(version_id),
            'version_number': version.version_number,
            'environment': environment,
            'user_id': str(user_id)
        }
    )
    
    # Get current keys to compare with snapshot
    current_keys = set(ConfigValue.objects.filter(
        config_object=config_object, 
        environment=environment
    ).values_list('key', flat=True))
    
    snapshot_keys = set(v['key'] for v in values)
    
    # 1. Delete keys that are not in the snapshot
    keys_to_delete = current_keys - snapshot_keys
    if keys_to_delete:
        ConfigValue.objects.filter(
            config_object=config_object,
            environment=environment,
            key__in=keys_to_delete
        ).delete()
        
    # 2. Restore values from snapshot
    for val_data in values:
        ConfigValue.objects.update_or_create(
            config_object=config_object,
            environment=environment,
            key=val_data['key'],
            defaults={
                'value_type': val_data['value_type'],
                'value_string': val_data.get('value_string'),
                'value_json': val_data.get('value_json'),
                'value_reference_id': val_data.get('reference_id')
            }
        )
        
    # 3. Create a new version for this rollback
    create_config_version(
        config_object=config_object,
        environment=environment,
        user_id=user_id,
        change_summary=f"Rolled back to v{version.version_number}"
    )
    
    # Cache invalidation on commit (outside transaction)
    asset_id = config_object.asset.id
    transaction.on_commit(lambda: invalidate_config_cache(asset_id, environment))
    
    # Log activity on commit
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
        transaction.on_commit(lambda: log_activity(
            user=user,
            action="Rolled Back Config",
            target=f"{config_object.name} (v{version.version_number})",
            details={
                "asset_slug": config_object.asset.slug,
                "config_object": config_object.name,
                "version": version.version_number,
                "environment": environment
            }
        ))
    except User.DoesNotExist:
        logger.warning(f"User {user_id} not found for activity log")
    
    return True
