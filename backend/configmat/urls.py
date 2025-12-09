from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # API Endpoints
    # Public API (for SDKs, CLI, external integrations)
    path('api/v1/', include('apps.api.v1.urls')),
    
    # Internal APIs
    path('api/', include('apps.authentication.urls')),
    path('api/', include('apps.config_assets.urls')),
    path('api/', include('apps.api_keys.urls')),
    path('api/', include('apps.audit.urls')),
    path('api/chat/', include('apps.chat.urls')),
]
