class CapabilityService:
    """
    Open Source Implementation:
    By default, ConfigMat OSS is permissive. 
    Self-hosters get access to features without tier restrictions.
    """
    
    @staticmethod
    def can_access_audit_logs(tenant):
        return True

    @staticmethod
    def get_max_seats(tenant):
        # OSS allows unlimited seats effectively
        return 999999
