"""
URL configuration for Public API v1.
Simplified endpoints - organization is derived from API key.
"""

from django.urls import path
from apps.api.v1.views import health, me
from apps.api.v1.views import values_simple, assets_simple

app_name = 'api_v1'

urlpatterns = [
    # Health check (no auth required)
    path('health/', health.HealthCheckView.as_view(), name='health'),
    
    # API Key metadata (get org, env from API key)
    path('me/', me.APIKeyMetadataView.as_view(), name='api-key-metadata'),
    
    # Assets (simplified - org from API key)
    path(
        'assets/',
        assets_simple.AssetListView.as_view(),
        name='asset-list'
    ),
    path(
        'assets/<str:asset>/',
        assets_simple.AssetDetailView.as_view(),
        name='asset-detail'
    ),
    
    # Config values (simplified - org from API key)
    path(
        'assets/<str:asset>/values/',
        values_simple.ConfigValuesView.as_view(),
        name='config-values'
    ),
    
    # Granular config value (simplified - org from API key)
    path(
        'assets/<str:asset>/objects/<str:object_name>/values/<str:key>/',
        values_simple.ConfigValueDetailView.as_view(),
        name='config-value-detail'
    ),
]
