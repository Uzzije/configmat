from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Tenant
from .org_models import Environment

@receiver(post_save, sender=Tenant)
def create_default_environments(sender, instance, created, **kwargs):
    if created:
        Environment.objects.get_or_create(
            tenant=instance,
            slug='local',
            defaults={'name': 'Local', 'order': 1}
        )
        Environment.objects.get_or_create(
            tenant=instance,
            slug='stage',
            defaults={'name': 'Stage', 'order': 2}
        )
        Environment.objects.get_or_create(
            tenant=instance,
            slug='production',
            defaults={'name': 'Production', 'order': 3}
        )
