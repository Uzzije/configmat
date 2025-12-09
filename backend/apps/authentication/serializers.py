from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.db import transaction
from django.utils import timezone
from .models import User, Tenant, TenantMembership, TenantInvitation


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['id', 'name', 'slug']


class UserSerializer(serializers.ModelSerializer):
    tenant = TenantSerializer(read_only=True)
    current_tenant = TenantSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'role', 'tenant', 'current_tenant']
        read_only_fields = ['id', 'email', 'role', 'tenant', 'current_tenant']


class TenantMembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = TenantMembership
        fields = ['id', 'user', 'role', 'joined_at']
        read_only_fields = ['id', 'user', 'joined_at']


class TenantInvitationSerializer(serializers.ModelSerializer):
    invited_by = UserSerializer(read_only=True)
    
    class Meta:
        model = TenantInvitation
        fields = ['id', 'email', 'role', 'status', 'invited_by', 'created_at', 'expires_at']
        read_only_fields = ['id', 'status', 'invited_by', 'created_at', 'expires_at']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    tenant_name = serializers.CharField(write_only=True, required=False)
    invite_token = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name', 'tenant_name', 'invite_token']

    def validate(self, data):
        if not data.get('tenant_name') and not data.get('invite_token'):
            raise serializers.ValidationError("Either tenant_name or invite_token is required.")
        
        if data.get('invite_token'):
            try:
                invite = TenantInvitation.objects.get(token=data['invite_token'], status='pending')
                if invite.expires_at < timezone.now():
                    raise serializers.ValidationError({"invite_token": "Invitation has expired."})
                if invite.email != data['email']:
                    raise serializers.ValidationError({"email": "Email does not match invitation."})
            except TenantInvitation.DoesNotExist:
                raise serializers.ValidationError({"invite_token": "Invalid invitation token."})
                
        return data

    def create(self, validated_data):
        tenant_name = validated_data.get('tenant_name')
        invite_token = validated_data.get('invite_token')
        password = validated_data.pop('password')
        
        with transaction.atomic():
            if invite_token:
                # Join existing tenant
                invite = TenantInvitation.objects.get(token=invite_token)
                tenant = invite.tenant
                role = invite.role
                
                # Create User
                user = User.objects.create_user(
                    username=validated_data['email'],
                    email=validated_data['email'],
                    password=password,
                    first_name=validated_data.get('first_name', ''),
                    last_name=validated_data.get('last_name', ''),
                    tenant=tenant, # Set default tenant
                    current_tenant=tenant,
                    role=role
                )
                
                # Create Membership
                TenantMembership.objects.create(user=user, tenant=tenant, role=role)
                
                # Mark invite accepted
                invite.status = 'accepted'
                invite.save()
                
            else:
                # Create New Tenant
                # Simple slug generation
                slug = tenant_name.lower().replace(' ', '-')
                base_slug = slug
                counter = 1
                while Tenant.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                    
                tenant = Tenant.objects.create(name=tenant_name, slug=slug)
                
                # Create User
                user = User.objects.create_user(
                    username=validated_data['email'],
                    email=validated_data['email'],
                    password=password,
                    first_name=validated_data.get('first_name', ''),
                    last_name=validated_data.get('last_name', ''),
                    tenant=tenant,
                    current_tenant=tenant,
                    role='admin'
                )
                
                # Create Membership
                TenantMembership.objects.create(user=user, tenant=tenant, role='admin')
            
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom token serializer to include user info in response"""
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add extra user data to the response
        user_data = UserSerializer(self.user).data
        data['user'] = user_data
        
        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    uidb64 = serializers.CharField()
    password = serializers.CharField(write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
