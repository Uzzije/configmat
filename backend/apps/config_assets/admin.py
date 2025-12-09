from django.contrib import admin
from .models import ConfigAsset, ConfigObject, ConfigValue, ConfigVersion, EncryptionKey

@admin.register(ConfigAsset)
class ConfigAssetAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'context_type', 'context', 'tenant', 'created_by', 'updated_at')
    list_filter = ('context_type', 'tenant', 'created_at')
    search_fields = ('name', 'slug', 'context', 'tenant__name')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(ConfigObject)
class ConfigObjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'asset', 'object_type', 'created_at')
    list_filter = ('object_type', 'asset__tenant')
    search_fields = ('name', 'asset__name')

@admin.register(ConfigValue)
class ConfigValueAdmin(admin.ModelAdmin):
    list_display = ('key', 'config_object', 'environment', 'value_type', 'updated_at')
    list_filter = ('environment', 'value_type', 'config_object__asset__tenant')
    search_fields = ('key', 'value_string', 'config_object__name')

@admin.register(ConfigVersion)
class ConfigVersionAdmin(admin.ModelAdmin):
    list_display = ('config_object', 'environment', 'version_number', 'updated_by', 'updated_at')
    list_filter = ('environment', 'config_object__asset__tenant')
    search_fields = ('config_object__name', 'change_summary')

@admin.register(EncryptionKey)
class EncryptionKeyAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant', 'created_at', 'rotated_at')
    list_filter = ('tenant', 'created_at')
    readonly_fields = ('encrypted_dek',) # Don't allow editing the blob manually

