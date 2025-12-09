from django.urls import reverse
from rest_framework.test import APITestCase
from apps.authentication.models import User, Tenant
from apps.config_assets.models import ConfigAsset, ConfigObject
from django.db import connection

class RLSTestCase(APITestCase):
    def setUp(self):
        # Create Tenants
        self.tenant_a = Tenant.objects.create(name='Tenant A', slug='tenant-a')
        self.tenant_b = Tenant.objects.create(name='Tenant B', slug='tenant-b')

        # Create Users
        self.user_a = User.objects.create_user(email='user_a@example.com', password='password', tenant=self.tenant_a, current_tenant=self.tenant_a)
        self.user_b = User.objects.create_user(email='user_b@example.com', password='password', tenant=self.tenant_b, current_tenant=self.tenant_b)

        # Create Assets directly (Bypassing RLS for setup? No, setup runs as superuser usually or we need to ensure context)
        # In tests, ORM usually bypasses RLS unless we enforce it or we are logged in as restricted user?
        # NO. Enables RLS applies to ALL roles unless BYPASSRLS attribute is set.
        # Superuser (DB owner) usually has BYPASSRLS.
        # Code running here likely runs as DB superuser (postgres/configmat).
        
        # We need to explicitly Set context for setup if RLS is active and blocking us?
        # If the DB user has BYPASSRLS (which 'configmat' likely does if it owns the DB/Tables), we can create freely.
        
        self.asset_a = ConfigAsset.objects.create(tenant=self.tenant_a, name='Asset A', slug='asset-a')
        self.asset_b = ConfigAsset.objects.create(tenant=self.tenant_b, name='Asset B', slug='asset-b')

    def test_rls_isolation(self):
        # Authenticate as User A
        self.client.force_authenticate(user=self.user_a)
        
        # User A should only see Asset A
        url = reverse('asset-list') 
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['slug'], 'asset-a')

        # Authenticate as User B
        self.client.force_authenticate(user=self.user_b)
        
        # User B should only see Asset B
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['slug'], 'asset-b')

    def test_direct_access_blocked(self):
        # User A tries to access Asset B by ID/Slug
        self.client.force_authenticate(user=self.user_a)
        
        url = reverse('asset-detail', args=[self.asset_b.slug])
        response = self.client.get(url)
        # Should be 404 because RLS hides the row
        self.assertEqual(response.status_code, 404) 

