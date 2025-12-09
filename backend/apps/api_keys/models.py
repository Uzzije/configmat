import uuid
import hashlib
import bcrypt
from django.db import models
from django.conf import settings
from apps.authentication.models import Tenant
from apps.config_assets.models import ConfigAsset


class APIKey(models.Model):
    """API keys for programmatic access"""
    SCOPE_CHOICES = [
        ('tenant', 'Tenant-wide'),
        ('asset', 'Asset-specific'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='api_keys'
    )
    asset = models.ForeignKey(
        ConfigAsset,
        on_delete=models.CASCADE,
        related_name='api_keys',
        null=True,
        blank=True,
        help_text='If set, key is scoped to this asset only'
    )
    scope = models.CharField(
        max_length=20,
        choices=SCOPE_CHOICES,
        default='tenant',
        help_text='Scope of the API key'
    )
    ENVIRONMENT_CHOICES = [
        ('local', 'Local'),
        ('stage', 'Stage'),
        ('prod', 'Production'),
    ]
    environment = models.CharField(
        max_length=20,
        choices=ENVIRONMENT_CHOICES,
        default='local',
        help_text='Environment this key is scoped to'
    )
    key_hash = models.CharField(max_length=255, unique=True)
    key_prefix = models.CharField(max_length=16)  # For display: cm_abc123...
    label = models.CharField(max_length=255)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'api_keys'
        ordering = ['-created_at']

    def __str__(self):
        scope_str = f"/{self.asset.slug}" if self.asset else ""
        return f"{self.tenant.name}{scope_str}/{self.label} ({self.key_prefix}...)"

    @staticmethod
    def generate_org_hash(tenant_slug: str) -> str:
        """Generate a short hash from tenant slug for security"""
        hash_obj = hashlib.sha256(tenant_slug.encode())
        return hash_obj.hexdigest()[:8]

    @staticmethod
    def hash_key(key: str) -> str:
        """Hash an API key using bcrypt"""
        return bcrypt.hashpw(key.encode(), bcrypt.gensalt()).decode()

    def verify_key(self, key: str) -> bool:
        """Verify a key against the stored hash"""
        return bcrypt.checkpw(key.encode(), self.key_hash.encode())
