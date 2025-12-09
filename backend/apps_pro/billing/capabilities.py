from apps.authentication.models import Tenant

class SaaSCapabilityService:
    """
    SaaS/Enterprise Implementation:
    Enforces strict limits based on the paid plan (Tier).
    """
    
    @staticmethod
    def can_access_audit_logs(tenant):
        # Only Pro & Enterprise get Audit Logs
        return tenant.tier in ['pro', 'enterprise']

    @staticmethod
    def get_max_seats(tenant):
        # Strict seat limits for SaaS tiers
        # Note: In a real app, 'pro' might be higher or handled via Stripe quantity
        limits = {
            'free': 1,
            'starter': 4,
            'pro': 100,
            'enterprise': 1000
        }
        return limits.get(tenant.tier, 1)
