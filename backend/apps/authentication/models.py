import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class Tenant(models.Model):
    """Organization/Workspace model for multi-tenancy"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tenants'
        ordering = ['name']

    TIER_CHOICES = [
        ('free', 'Free'),
        ('starter', 'Starter'),
        ('pro', 'Pro'),
        ('enterprise', 'Enterprise'),
    ]
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='free')

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    """Custom user manager to handle tenant assignment"""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')

        # Ensure a default tenant exists for the superuser
        if 'tenant' not in extra_fields:
            default_tenant, _ = Tenant.objects.get_or_create(
                slug='default',
                defaults={'name': 'Default Organization'}
            )
            extra_fields['tenant'] = default_tenant
            extra_fields['current_tenant'] = default_tenant

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom user model with tenant and role support"""
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('user', 'User'),
    ]

    objects = UserManager()

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    # Primary/Default tenant (Legacy support)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='users'
    )
    # Active context for multi-tenant users
    current_tenant = models.ForeignKey(
        Tenant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='active_users'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Override username requirement from AbstractUser
    username = models.CharField(max_length=150, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']  # Required for createsuperuser

    class Meta:
        db_table = 'users'
        ordering = ['email']

    def __str__(self):
        return self.email


class TenantMembership(models.Model):
    """Link between User and Tenant with role"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=User.ROLE_CHOICES, default='user')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tenant_memberships'
        unique_together = ('user', 'tenant')

    def __str__(self):
        return f"{self.user.email} in {self.tenant.name}"


class TenantInvitation(models.Model):
    """Pending invitation to join a tenant"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='invitations')
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=User.ROLE_CHOICES, default='user')
    token = models.CharField(max_length=64, unique=True)
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('expired', 'Expired')],
        default='pending'
    )

    class Meta:
        db_table = 'tenant_invitations'
        ordering = ['-created_at']

    def __str__(self):
        return f"Invite for {self.email} to {self.tenant.name}"
