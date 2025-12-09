from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError as DjangoValidationError
from .org_models import ContextType, Environment
from .org_serializers import TenantSerializer, ContextTypeSerializer, EnvironmentSerializer
from .models import Tenant


class TenantViewSet(viewsets.ModelViewSet):
    """Manage organization/tenant settings"""
    serializer_class = TenantSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'patch', 'post']  # Only allow read, update, and switch (post)

    def get_queryset(self):
        """Return only the current user's tenant"""
        tenant = self.request.user.current_tenant or self.request.user.tenant
        return Tenant.objects.filter(id=tenant.id)

    def get_object(self):
        """Return the current tenant"""
        return self.request.user.current_tenant or self.request.user.tenant

    @action(detail=False, methods=['get'])
    def my_tenants(self, request):
        """List all tenants the user is a member of"""
        tenants = Tenant.objects.filter(memberships__user=request.user)
        serializer = self.get_serializer(tenants, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def switch(self, request, pk=None):
        """Switch current tenant context"""
        try:
            # Verify membership
            tenant = Tenant.objects.get(pk=pk, memberships__user=request.user)
        except Tenant.DoesNotExist:
            return Response({'error': 'Tenant not found or access denied'}, status=404)
            
        request.user.current_tenant = tenant
        request.user.save()
        return Response({'status': 'switched', 'tenant': TenantSerializer(tenant).data})


class ContextTypeViewSet(viewsets.ModelViewSet):
    """Manage context types for the organization"""
    serializer_class = ContextTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_queryset(self):
        tenant = self.request.user.current_tenant or self.request.user.tenant
        return ContextType.objects.filter(tenant=tenant)

    def perform_destroy(self, instance):
        """Override to handle validation errors gracefully"""
        try:
            instance.delete()
        except DjangoValidationError as e:
            # Convert Django ValidationError to DRF response
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, *args, **kwargs):
        """Custom destroy to catch validation errors"""
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except DjangoValidationError as e:
            return Response(
                {'error': str(e.message) if hasattr(e, 'message') else str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class EnvironmentViewSet(viewsets.ModelViewSet):
    """Manage deployment environments for the organization"""
    serializer_class = EnvironmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_queryset(self):
        tenant = self.request.user.current_tenant or self.request.user.tenant
        return Environment.objects.filter(tenant=tenant)

    def perform_destroy(self, instance):
        """Override to handle validation errors gracefully"""
        try:
            instance.delete()
        except DjangoValidationError as e:
            # Convert Django ValidationError to DRF response
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, *args, **kwargs):
        """Custom destroy to catch validation errors"""
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except DjangoValidationError as e:
            return Response(
                {'error': str(e.message) if hasattr(e, 'message') else str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def reorder(self, request):
        """Reorder environments based on provided order"""
        tenant = request.user.current_tenant or request.user.tenant
        environment_ids = request.data.get('order', [])
        
        if not isinstance(environment_ids, list):
            return Response(
                {'error': 'Order must be a list of environment IDs'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update order for each environment
        for index, env_id in enumerate(environment_ids):
            try:
                env = Environment.objects.get(id=env_id, tenant=tenant)
                env.order = index
                env.save()
            except Environment.DoesNotExist:
                pass
        
        # Return updated list
        environments = Environment.objects.filter(tenant=tenant)
        serializer = self.get_serializer(environments, many=True)
        return Response(serializer.data)
