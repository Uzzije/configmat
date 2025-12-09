from .models import ActivityLog

def log_activity(user, action, target="", details=None, tenant=None):
    """
    Log a user activity.
    """
    if not user or not user.is_authenticated:
        return
        
    if details is None:
        details = {}
        
    # If tenant is not provided, try to get from user
    if not tenant:
        if hasattr(user, 'tenant'):
            tenant = user.tenant
        
    if not tenant:
        # Should not happen for authenticated users in this system, but safe guard
        return

    ActivityLog.objects.create(
        tenant=tenant,
        user=user,
        action=action,
        target=target,
        details=details
    )
