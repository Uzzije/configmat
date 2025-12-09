import secrets
from datetime import timedelta
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
from django.utils.module_loading import import_string
from .models import TenantMembership, TenantInvitation
from .serializers import TenantMembershipSerializer, TenantInvitationSerializer


class IsAdminUser(permissions.BasePermission):
    """Only allow admin users to perform actions"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class TenantMembershipViewSet(viewsets.ModelViewSet):
    """Manage team members within current tenant"""
    serializer_class = TenantMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Get current tenant from user
        tenant = self.request.user.current_tenant or self.request.user.tenant
        return TenantMembership.objects.filter(tenant=tenant).select_related('user')
    
    def get_permissions(self):
        # Only admins can create, update, or delete memberships
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return super().get_permissions()
    
    def destroy(self, request, *args, **kwargs):
        """Remove a user from the tenant"""
        membership = self.get_object()
        
        # Prevent removing yourself
        if membership.user == request.user:
            return Response(
                {"error": "You cannot remove yourself from the organization."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Prevent removing the last admin
        tenant = request.user.current_tenant or request.user.tenant
        admin_count = TenantMembership.objects.filter(tenant=tenant, role='admin').count()
        if membership.role == 'admin' and admin_count <= 1:
            return Response(
                {"error": "Cannot remove the last admin from the organization."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def update(self, request, *args, **kwargs):
        """Update member role"""
        membership = self.get_object()
        
        # Prevent changing your own role
        if membership.user == request.user:
            return Response(
                {"error": "You cannot change your own role."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Prevent demoting the last admin
        tenant = request.user.current_tenant or request.user.tenant
        if membership.role == 'admin' and request.data.get('role') != 'admin':
            admin_count = TenantMembership.objects.filter(tenant=tenant, role='admin').count()
            if admin_count <= 1:
                return Response(
                    {"error": "Cannot demote the last admin."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return super().update(request, *args, **kwargs)


class TenantInvitationViewSet(viewsets.ModelViewSet):
    """Manage invitations to join tenant"""
    serializer_class = TenantInvitationSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        tenant = self.request.user.current_tenant or self.request.user.tenant
        return TenantInvitation.objects.filter(tenant=tenant)
    
    def create(self, request, *args, **kwargs):
        """Create a new invitation"""
        email = request.data.get('email')
        role = request.data.get('role', 'user')
        tenant = request.user.current_tenant or request.user.tenant
        
        # --- Feature Gate: Team Size ---
        CapabilityService = import_string(settings.CAPABILITY_SERVICE)
        max_seats = CapabilityService.get_max_seats(tenant)
        
        current_members = TenantMembership.objects.filter(tenant=tenant).count()
        pending_invites = TenantInvitation.objects.filter(tenant=tenant, status='pending').count()
        total_seats_used = current_members + pending_invites
        
        if total_seats_used >= max_seats:
             return Response(
                {"error": f"Plan limit reached. Your {tenant.tier.title()} plan allows {max_seats} users. Upgrade to add more people."},
                status=status.HTTP_403_FORBIDDEN
            )
        # -------------------------------
        
        # Check if user already exists in this tenant
        from .models import User
        try:
            user = User.objects.get(email=email)
            if TenantMembership.objects.filter(user=user, tenant=tenant).exists():
                return Response(
                    {"error": "User is already a member of this organization."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except User.DoesNotExist:
            pass
        
        # Check for existing pending invitation
        existing_invite = TenantInvitation.objects.filter(
            tenant=tenant,
            email=email,
            status='pending'
        ).first()
        
        if existing_invite:
            return Response(
                {"error": "An invitation has already been sent to this email."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate secure token
        token = secrets.token_urlsafe(32)
        
        # Create invitation
        invitation = TenantInvitation.objects.create(
            tenant=tenant,
            email=email,
            role=role,
            token=token,
            invited_by=request.user,
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        # Send email with invitation link
        from django.conf import settings
        from .email_service import send_invitation_email
        
        invite_url = f"{settings.FRONTEND_URL}/register?token={token}"
        email_sent = send_invitation_email(email, invite_url, request.user.first_name or request.user.email)
        
        serializer = self.get_serializer(invitation)
        response_data = serializer.data
        response_data['invite_url'] = invite_url
        response_data['email_sent'] = email_sent
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def resend(self, request, pk=None):
        """Resend an invitation"""
        invitation = self.get_object()
        
        if invitation.status != 'pending':
            return Response(
                {"error": "Can only resend pending invitations."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Extend expiration
        invitation.expires_at = timezone.now() + timedelta(days=7)
        invitation.save()
        
        # Send email
        from django.conf import settings
        from .email_service import send_invitation_email
        
        invite_url = f"{settings.FRONTEND_URL}/register?token={invitation.token}"
        email_sent = send_invitation_email(invitation.email, invite_url, request.user.first_name or request.user.email)
        
        return Response({"message": "Invitation resent successfully.", "email_sent": email_sent})
    
    def destroy(self, request, *args, **kwargs):
        """Revoke an invitation"""
        invitation = self.get_object()
        
        if invitation.status != 'pending':
            return Response(
                {"error": "Can only revoke pending invitations."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        invitation.status = 'expired'
        invitation.save()
        
        return Response(status=status.HTTP_204_NO_CONTENT)
