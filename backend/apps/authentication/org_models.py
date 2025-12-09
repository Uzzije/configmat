import uuid
from django.db import models
from django.core.exceptions import ValidationError


class ContextType(models.Model):
    """Context types for organizing configuration assets"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'authentication.Tenant',
        on_delete=models.CASCADE,
        related_name='context_types'
    )
    CONTEXT_TYPE_CHOICES = [
        ('product', 'Product'),
        ('team', 'Team'),
    ]
    type = models.CharField(max_length=100, choices=CONTEXT_TYPE_CHOICES, help_text='Context type name (product or team)')
    category = models.CharField(max_length=100, help_text='Category for grouping (e.g., specific team name or product name)')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'context_types'
        unique_together = [('tenant', 'type', 'category')]
        ordering = ['type', 'category']

    def __str__(self):
        return f"{self.type} → {self.category}"

    def delete(self, *args, **kwargs):
        """Prevent deletion if context type is in use"""
        from apps.config_assets.models import ConfigAsset
        
        # Check if any assets use this context type
        assets_count = ConfigAsset.objects.filter(
            tenant=self.tenant,
            context_type=self.type
        ).count()
        
        if assets_count > 0:
            raise ValidationError(
                f"Cannot delete context type '{self.type}'. "
                f"It is used by {assets_count} asset(s). "
                f"Please reassign or delete those assets first."
            )
        
        super().delete(*args, **kwargs)


class Environment(models.Model):
    """Deployment environments for configurations"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'authentication.Tenant',
        on_delete=models.CASCADE,
        related_name='environments'
    )
    name = models.CharField(max_length=100, help_text='Display name (e.g., Development)')
    slug = models.SlugField(max_length=100, help_text='URL-friendly identifier (e.g., dev)')
    order = models.IntegerField(default=0, help_text='Display order')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'environments'
        unique_together = [('tenant', 'slug')]
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.name} ({self.slug})"

    def delete(self, *args, **kwargs):
        """Prevent deletion if environment has config values"""
        from apps.config_assets.models import ConfigValue
        
        # Check if any config values use this environment
        values_count = ConfigValue.objects.filter(
            config_object__asset__tenant=self.tenant,
            environment=self.slug
        ).count()
        
        if values_count > 0:
            raise ValidationError(
                f"Cannot delete environment '{self.name}'. "
                f"It contains {values_count} configuration value(s). "
                f"Please delete those values first."
            )
        
        super().delete(*args, **kwargs)
