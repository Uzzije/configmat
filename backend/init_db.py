import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'configmat.settings')
django.setup()

from apps.authentication.models import Tenant, User

def init_db():
    # Create default tenant
    tenant, created = Tenant.objects.get_or_create(
        slug='default',
        defaults={'name': 'Default Organization'}
    )
    if created:
        print(f"Created default tenant: {tenant.name}")
    else:
        print(f"Found existing tenant: {tenant.name}")

    # Create superuser
    if not User.objects.filter(email='admin@configmat.com').exists():
        User.objects.create_superuser(
            email='admin@configmat.com',
            username='admin',
            password='adminpassword123',
            tenant=tenant,
            role='admin'
        )
        print("Created superuser: admin@configmat.com")
    else:
        print("Superuser already exists")

if __name__ == '__main__':
    init_db()
