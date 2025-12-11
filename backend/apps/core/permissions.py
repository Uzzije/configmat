import logging
from rest_framework.permissions import BasePermission
from django.db import connection

logger = logging.getLogger(__name__)


def set_tenant_context(cursor, tenant_id: str) -> None:
    """
    Safely set the PostgreSQL tenant context using parameterized query.
    
    Uses set_config() instead of SET to allow parameterized queries,
    preventing SQL injection attacks.
    
    Args:
        cursor: Database cursor
        tenant_id: UUID string of the tenant
    """
    # set_config(setting_name, new_value, is_local)
    # is_local=false means the setting persists for the connection
    cursor.execute(
        "SELECT set_config('app.current_tenant', %s, false)",
        [str(tenant_id)]
    )


def reset_tenant_context(cursor) -> None:
    """Reset the tenant context to empty."""
    cursor.execute("RESET app.current_tenant;")


class TenantContextPermission(BasePermission):
    """
    Sets the Postgres RLS context for the authenticated user.
    This runs after DRF Authentication, so request.user is available (even for JWT).
    
    Security: Uses parameterized queries via set_config() to prevent SQL injection.
    """
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            if hasattr(request.user, 'current_tenant') and request.user.current_tenant:
                with connection.cursor() as cursor:
                    set_tenant_context(cursor, request.user.current_tenant.id)
                    logger.debug(
                        "Set tenant context for user",
                        extra={
                            'user_id': str(request.user.id),
                            'tenant_id': str(request.user.current_tenant.id)
                        }
                    )
        elif request.auth and hasattr(request.auth, 'tenant'):
            # Handle API Key Authentication where user might be None but Auth (Key) has tenant
            with connection.cursor() as cursor:
                set_tenant_context(cursor, request.auth.tenant.id)
                logger.debug(
                    "Set tenant context for API key",
                    extra={'tenant_id': str(request.auth.tenant.id)}
                )
        else:
            # Ensure context is reset for anonymous or unauthed requests
            # Middleware handles RESET at start. This handles setting it if Auth succeeded.
            pass
        return True  # We don't block permission here, just set context. Use IsAuthenticated for blocking.

class HasAPIKey(BasePermission):
    """
    Allows access if a valid API Key is present in request.auth.
    """
    def has_permission(self, request, view):
        return bool(request.auth and hasattr(request.auth, 'tenant'))
