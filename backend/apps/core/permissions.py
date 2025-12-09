from rest_framework.permissions import BasePermission
from django.db import connection

class TenantContextPermission(BasePermission):
    """
    Sets the Postgres RLS context for the authenticated user.
    This runs after DRF Authentication, so request.user is available (even for JWT).
    """
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            if hasattr(request.user, 'current_tenant') and request.user.current_tenant:
                with connection.cursor() as cursor:
                    cursor.execute(f"SET app.current_tenant = '{request.user.current_tenant.id}';")
        elif request.auth and hasattr(request.auth, 'tenant'):
            # Handle API Key Authentication where user might be None but Auth (Key) has tenant
             with connection.cursor() as cursor:
                 cursor.execute(f"SET app.current_tenant = '{request.auth.tenant.id}';")
        else:
             # Ensure context is reset for anonymous or unauthed requests (though connection pooling safety usually requires RESET at start/end)
             # Middleware handles RESET at start. This handles setting it if Auth succeeded.
             pass
        return True # We don't block permission here, just set context. Use IsAuthenticated for blocking.

class HasAPIKey(BasePermission):
    """
    Allows access if a valid API Key is present in request.auth.
    """
    def has_permission(self, request, view):
        return bool(request.auth and hasattr(request.auth, 'tenant'))
