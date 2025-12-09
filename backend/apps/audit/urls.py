from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ActivityLogViewSet

router = DefaultRouter()
router.register(r'audit-logs', ActivityLogViewSet, basename='audit-log')

urlpatterns = [
    path('', include(router.urls)),
]
