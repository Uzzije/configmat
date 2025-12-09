from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import APIKey
from .serializers import APIKeySerializer


class APIKeyViewSet(viewsets.ModelViewSet):
    """Manage API Keys - All authenticated users can view and create keys"""
    serializer_class = APIKeySerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'delete']

    def get_queryset(self):
        """Return API keys for the current tenant"""
        tenant = self.request.user.current_tenant or self.request.user.tenant
        return APIKey.objects.filter(
            tenant=tenant,
            revoked=False
        ).select_related('asset', 'created_by')

    def perform_destroy(self, instance):
        """Soft delete (revoke) instead of actual delete
        Users can revoke their own keys, admins can revoke any key"""
        # Check if user is admin or owns the key
        if self.request.user.role != 'admin' and instance.created_by != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only revoke your own API keys.")
        
        instance.revoked = True
        instance.revoked_at = timezone.now()
        instance.save()

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """Explicit revoke endpoint
        Users can revoke their own keys, admins can revoke any key"""
        api_key = self.get_object()
        
        # Check if user is admin or owns the key
        if request.user.role != 'admin' and api_key.created_by != request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only revoke your own API keys.")
        
        api_key.revoked = True
        api_key.revoked_at = timezone.now()
        api_key.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
