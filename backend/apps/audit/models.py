from django.db import models
from django.conf import settings
from apps.authentication.models import Tenant


class ActivityLog(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='activities')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='activities')
    action = models.CharField(max_length=255)
    target = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)
    
    # Merkle Chain Fields
    # Initially null to allow migration of existing rows, or we flush them.
    hash = models.CharField(max_length=64, unique=True, editable=False, null=True) 
    previous_hash = models.CharField(max_length=64, editable=False, null=True) # Null for genesis block
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
             models.Index(fields=['hash']),
             models.Index(fields=['previous_hash']),
        ]

    def __str__(self):
        return f"{self.user} - {self.action} - {self.hash[:8]}"

    def save(self, *args, **kwargs):
        if self.pk:
            # Prevent updates to existing logs (WORM)
            raise ValueError("ActivityLog is immutable and cannot be modified.")
        
        # Calculate Hash
        self.calculate_hash()
        super().save(*args, **kwargs)

    def calculate_hash(self):
        import hashlib
        import json
        
        # Find previous log for this tenant to chain
        # Note: concurrency race condition possible here. 
        # For strict chain, we need locking or single-writer queue (like Dramatiq/Celery default behavior if strictly ordered).
        # For MVP/PoC, we fetch latest.
        last_log = ActivityLog.objects.filter(tenant=self.tenant).order_by('-created_at').first()
        
        if last_log:
            self.previous_hash = last_log.hash
        else:
            self.previous_hash = '0' * 64 # Genesis hash

        # Data to hash
        data = f"{self.previous_hash}{self.action}{self.target}{json.dumps(self.details, sort_keys=True)}"
        self.hash = hashlib.sha256(data.encode('utf-8')).hexdigest()

