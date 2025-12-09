from rest_framework import viewsets, permissions, filters
from rest_framework.exceptions import PermissionDenied
from django.conf import settings
from django.utils.module_loading import import_string
from django_filters.rest_framework import DjangoFilterBackend
from .models import ActivityLog
from .serializers import ActivityLogSerializer

class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = {
        'user': ['exact'],
        'created_at': ['gte', 'lte']
    }
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        tenant = self.request.user.tenant
        
        # Swappable Capability Check
        CapabilityService = import_string(settings.CAPABILITY_SERVICE)
        
        if not CapabilityService.can_access_audit_logs(tenant):
            raise PermissionDenied("Audit Logs are not available on your current plan.")
            
        return ActivityLog.objects.filter(tenant=tenant)
