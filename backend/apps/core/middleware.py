import logging
from django.db import connection

logger = logging.getLogger(__name__)


class TenantContextMiddleware:
    """
    Middleware that sets the PostgreSQL current_tenant setting for RLS.
    
    Security: Uses parameterized queries via set_config() to prevent SQL injection.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def _set_config(self, cursor, setting: str, value: str) -> None:
        """
        Safely set a PostgreSQL config using parameterized query.
        
        Uses set_config() instead of SET to allow parameterized queries,
        preventing SQL injection attacks.
        """
        cursor.execute(
            "SELECT set_config(%s, %s, false)",
            [setting, value]
        )

    def _reset_config(self, cursor, setting: str) -> None:
        """Reset a PostgreSQL config setting."""
        # RESET doesn't need parameterization as setting name is hardcoded
        cursor.execute(f"RESET {setting};")

    def __call__(self, request):
        with connection.cursor() as cursor:
            if request.user.is_authenticated:
                # 1. Handle Superuser Bypass
                if request.user.is_superuser:
                    self._set_config(cursor, 'app.is_superuser', 'on')
                else:
                    self._reset_config(cursor, 'app.is_superuser')

                # 2. Handle Tenant Context
                if hasattr(request.user, 'current_tenant') and request.user.current_tenant:
                    self._set_config(
                        cursor, 
                        'app.current_tenant', 
                        str(request.user.current_tenant.id)
                    )
                    logger.debug(
                        "Middleware set tenant context",
                        extra={
                            'user_id': str(request.user.id),
                            'tenant_id': str(request.user.current_tenant.id)
                        }
                    )
                else:
                    self._reset_config(cursor, 'app.current_tenant')
            else:
                # Reset all for safety on unauthenticated requests
                self._reset_config(cursor, 'app.current_tenant')
                self._reset_config(cursor, 'app.is_superuser')

        response = self.get_response(request)
        return response
