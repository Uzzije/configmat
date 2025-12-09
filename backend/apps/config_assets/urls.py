from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ConfigAssetViewSet, ConfigObjectViewSet, 
    ConfigVersionViewSet, PublicConfigView
)
from .cli_views import (
    CLIOrganizationAssetsView,
    CLIAssetDetailView,
    CLIAssetValuesView,
    CLIHealthCheckView
)

router = DefaultRouter()
router.register(r'assets', ConfigAssetViewSet, basename='asset')
router.register(r'objects', ConfigObjectViewSet, basename='object')
router.register(r'versions', ConfigVersionViewSet, basename='version')

from .search_views import SemanticSearchView

urlpatterns = [
    # CLI-specific endpoints (organization-scoped)
    path('organizations/<str:org_slug>/assets/', CLIOrganizationAssetsView.as_view(), name='cli-org-assets'),
    path('organizations/<str:org_slug>/assets/<str:asset_slug>/', CLIAssetDetailView.as_view(), name='cli-asset-detail'),
    path('organizations/<str:org_slug>/assets/<str:asset_slug>/values/', CLIAssetValuesView.as_view(), name='cli-asset-values'),
    path('health/', CLIHealthCheckView.as_view(), name='cli-health'),
    
    # Existing endpoints
    path('search/', SemanticSearchView.as_view(), name='search'),
    path('public/<str:environment>/<str:asset_slug>/', PublicConfigView.as_view(), name='public-config'),
    path('', include(router.urls)),
]
