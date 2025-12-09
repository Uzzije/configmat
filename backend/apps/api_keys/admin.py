from django.contrib import admin
from .models import APIKey

@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ('label', 'key_prefix', 'tenant', 'scope', 'asset', 'created_by', 'created_at', 'revoked')
    list_filter = ('revoked', 'scope', 'tenant')
    search_fields = ('label', 'key_prefix', 'tenant__name')
    readonly_fields = ('key_hash', 'key_prefix', 'created_at', 'last_used_at', 'revoked_at')
