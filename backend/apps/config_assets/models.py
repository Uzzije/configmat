import uuid
from django.db import models
from django.conf import settings
from apps.authentication.models import Tenant


class EncryptionKey(models.Model):
    """Stores the Data Encryption Key (DEK) encrypted by the Master Key (KEK)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    encrypted_dek = models.BinaryField(help_text="DEK encrypted by KEK")
    created_at = models.DateTimeField(auto_now_add=True)
    rotated_at = models.DateTimeField(null=True, blank=True)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='encryption_keys'
    )

    class Meta:
        db_table = 'encryption_keys'
        ordering = ['-created_at']

    def __str__(self):
        return f"Key {self.id} for {self.tenant.name}"

class ConfigAsset(models.Model):
    """Top-level configuration asset"""
    CONTEXT_TYPE_CHOICES = [
        ('default', 'Default'),
        ('team', 'Team'),
        ('product', 'Product'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='config_assets'
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    description = models.TextField(blank=True)
    context_type = models.CharField(
        max_length=50,
        choices=CONTEXT_TYPE_CHOICES,
        default='default'
    )
    context = models.CharField(
        max_length=255,
        default='global',
        help_text='User-provided context name (e.g., "billing", "auth", "global")'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_assets'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'config_assets'
        unique_together = [('tenant', 'slug')]
        indexes = [
            models.Index(fields=['tenant', 'context_type']),
            models.Index(fields=['tenant', 'context']),
            models.Index(fields=['tenant', 'name']),
        ]
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.tenant.name}/{self.name}"


class ConfigObject(models.Model):
    """Individual config object within an asset"""
    OBJECT_TYPE_CHOICES = [
        ('json', 'JSON'),
        ('kv', 'Key-Value'),
        ('text', 'Text'),
        ('file', 'File'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(
        ConfigAsset,
        on_delete=models.CASCADE,
        related_name='config_objects'
    )
    name = models.CharField(max_length=255)
    object_type = models.CharField(max_length=20, choices=OBJECT_TYPE_CHOICES)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'config_objects'
        unique_together = [('asset', 'name')]
        ordering = ['name']

    def __str__(self):
        return f"{self.asset.name}/{self.name} ({self.object_type})"


class ConfigValue(models.Model):
    """Individual key-value pairs for KV type configs"""
    VALUE_TYPE_CHOICES = [
        ('string', 'String'),
        ('number', 'Number'),
        ('boolean', 'Boolean'),
        ('json', 'JSON'),
        ('reference', 'Reference'),
    ]

    ENVIRONMENT_CHOICES = [
        ('local', 'Local'),
        ('stage', 'Stage'),
        ('prod', 'Production'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    config_object = models.ForeignKey(
        ConfigObject,
        on_delete=models.CASCADE,
        related_name='values'
    )
    environment = models.CharField(max_length=20, choices=ENVIRONMENT_CHOICES)
    key = models.CharField(max_length=255)
    value_type = models.CharField(
        max_length=20,
        choices=VALUE_TYPE_CHOICES,
        default='string'
    )
    value_string = models.TextField(null=True, blank=True)
    value_json = models.JSONField(null=True, blank=True)
    
    # Zero-Knowledge Encryption Fields
    encryption_key = models.ForeignKey(
        EncryptionKey,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='encrypted_values',
        help_text='Key used to encrypt this value'
    )
    value_encrypted = models.BinaryField(null=True, blank=True, help_text='Encrypted value (AES-GCM)')
    
    value_reference = models.ForeignKey(
        ConfigObject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referenced_by',
        help_text='Reference to another config object'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'config_values'
        unique_together = [('config_object', 'environment', 'key')]
        indexes = [
            models.Index(fields=['config_object', 'environment']),
        ]
        ordering = ['key']

    def __str__(self):
        return f"{self.config_object.name}[{self.environment}]: {self.key}"


class ConfigVersion(models.Model):
    """Version history for config objects"""
    ENVIRONMENT_CHOICES = ConfigValue.ENVIRONMENT_CHOICES

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    config_object = models.ForeignKey(
        ConfigObject,
        on_delete=models.CASCADE,
        related_name='versions'
    )
    environment = models.CharField(max_length=20, choices=ENVIRONMENT_CHOICES)
    version_number = models.IntegerField()
    value_snapshot = models.JSONField(help_text='Complete snapshot of config at this version')
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    updated_at = models.DateTimeField(auto_now_add=True)
    change_summary = models.TextField(blank=True)

    class Meta:
        db_table = 'config_versions'
        unique_together = [('config_object', 'environment', 'version_number')]
        indexes = [
            models.Index(fields=['config_object', 'environment', '-version_number']),
        ]
        ordering = ['-version_number']

    def __str__(self):
        return f"{self.config_object.name} v{self.version_number} ({self.environment})"
