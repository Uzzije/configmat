import json
from django.core.cache import cache
from django.contrib.auth import get_user_model
from .models import ConfigAsset, ConfigValue, ConfigVersion
from apps.audit.services import log_activity

CACHE_TTL = 300  # 5 minutes

def get_resolved_config(asset_slug, environment, tenant_id):
    """
    Resolve configuration for a given asset and environment.
    Returns a dictionary of {object_name: resolved_value}.
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

    # Fetch all objects for this asset
    config_objects = asset.config_objects.all()
    
    resolved_config = {}
    
    for obj in config_objects:
        if obj.object_type == 'kv':
            # Resolve KV object as a dictionary of keys
            values = obj.values.filter(environment=environment)
            kv_dict = {}
            for val in values:
                if val.value_type == 'string':
                    kv_dict[val.key] = val.value_string
                elif val.value_type == 'number':
                    try:
                        kv_dict[val.key] = float(val.value_string)
                    except (ValueError, TypeError):
                        kv_dict[val.key] = 0
                elif val.value_type == 'boolean':
                    kv_dict[val.key] = val.value_string == 'true'
                elif val.value_type == 'json':
                    kv_dict[val.key] = val.value_json
                elif val.value_type == 'reference':
                    kv_dict[val.key] = {"_ref": str(val.value_reference_id)}
            
            resolved_config[obj.name] = kv_dict if values.exists() else {}
        else:
            # Non-KV (e.g. 'json' type), assume single value per environment
            value_obj = obj.values.filter(environment=environment).first()
            
            if value_obj:
                if value_obj.value_type == 'string':
                    resolved_config[obj.name] = value_obj.value_string
                elif value_obj.value_type == 'number':
                    try:
                        resolved_config[obj.name] = float(value_obj.value_string)
                    except (ValueError, TypeError):
                        resolved_config[obj.name] = 0
                elif value_obj.value_type == 'boolean':
                    resolved_config[obj.name] = value_obj.value_string == 'true'
                elif value_obj.value_type == 'json':
                    resolved_config[obj.name] = value_obj.value_json
                elif value_obj.value_type == 'reference':
                    resolved_config[obj.name] = {"_ref": str(value_obj.value_reference_id)}
            else:
                resolved_config[obj.name] = None

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


def promote_asset(asset_id, from_env, to_env, user_id):
    """
    Promote configuration from one environment to another.
    For KV objects: Syncs structure (keys). Adds new keys, removes obsolete keys. Preserves existing values.
    For other types: Overwrites target with source (since structure/data are inseparable).
    """
    try:
        asset = ConfigAsset.objects.get(id=asset_id)
    except ConfigAsset.DoesNotExist:
        return False

    # Get all objects for this asset
    config_objects = asset.config_objects.all()
    
    for obj in config_objects:
        # Get all source values
        source_values = obj.values.filter(environment=from_env)
        
        if not source_values.exists():
            # If source is empty, should we clear target? 
            # "Overwrite existing structure" implies yes.
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
        
    # Invalidate cache for target env
    invalidate_config_cache(asset.id, to_env)
    
    # Log activity
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
        log_activity(
            user=user,
            action="Promoted Asset",
            target=f"{asset.name} ({from_env} -> {to_env})",
            details={
                "asset_slug": asset.slug,
                "from_env": from_env,
                "to_env": to_env
            }
        )
    except User.DoesNotExist:
        pass
    
    return True


def rollback_to_version(version_id, user_id):
    """
    Rollback a config object to a specific version.
    """
    try:
        version = ConfigVersion.objects.get(id=version_id)
    except ConfigVersion.DoesNotExist:
        return False
        
    config_object = version.config_object
    environment = version.environment
    snapshot = version.value_snapshot
    values = snapshot.get('values', [])
    
    # 1. Clear existing values for this environment (optional, but safer to ensure exact match)
    # Actually, update_or_create handles updates. But if the old version didn't have a key that currently exists, 
    # we might want to delete the extra key?
    # For a true rollback, we should probably delete keys that weren't in the snapshot.
    
    current_keys = set(ConfigValue.objects.filter(
        config_object=config_object, 
        environment=environment
    ).values_list('key', flat=True))
    
    snapshot_keys = set(v['key'] for v in values)
    
    # Delete keys that are not in the snapshot
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
                'value_reference_id': val_data.get('reference_id') # Note: ID might be invalid if referenced object was deleted
            }
        )
        
    # 3. Create a new version for this rollback
    create_config_version(
        config_object=config_object,
        environment=environment,
        user_id=user_id,
        change_summary=f"Rolled back to v{version.version_number}"
    )
    
    # 4. Invalidate cache
    invalidate_config_cache(config_object.asset.id, environment)
    
    # Log activity
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
        log_activity(
            user=user,
            action="Rolled Back Config",
            target=f"{config_object.name} (v{version.version_number})",
            details={
                "asset_slug": config_object.asset.slug,
                "config_object": config_object.name,
                "version": version.version_number,
                "environment": environment
            }
        )
    except User.DoesNotExist:
        pass
    
    return True
