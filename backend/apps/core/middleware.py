from django.db import connection

class TenantContextMiddleware:
    """
    Middleware that sets the PostgreSQL current_tenant setting for RLS.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            with connection.cursor() as cursor:
                # 1. Handle Superuser Bypass
                if request.user.is_superuser:
                    cursor.execute("SET app.is_superuser = 'on';")
                else:
                    cursor.execute("RESET app.is_superuser;")

                # 2. Handle Tenant Context
                if hasattr(request.user, 'current_tenant') and request.user.current_tenant:
                    cursor.execute(f"SET app.current_tenant = '{request.user.current_tenant.id}';")
                else:
                    cursor.execute("RESET app.current_tenant;")
        else:
             # Reset all for safety
             with connection.cursor() as cursor:
                 cursor.execute("RESET app.current_tenant;")
                 cursor.execute("RESET app.is_superuser;")

        response = self.get_response(request)
        return response
