from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from apps.authentication.models import User, Tenant

class AuditTierGatingTest(APITestCase):
    def setUp(self):
        # Create Tenants
        self.free_tenant = Tenant.objects.create(name="Free Org", slug="free-org", tier='free')
        self.pro_tenant = Tenant.objects.create(name="Pro Org", slug="pro-org", tier='pro')
        
        # Create Users
        self.free_user = User.objects.create_user(email="free@example.com", password="password", tenant=self.free_tenant)
        self.pro_user = User.objects.create_user(email="pro@example.com", password="password", tenant=self.pro_tenant)
        
        self.url = "/api/audit-logs/"

    def test_free_tier_cannot_access_audit_logs(self):
        self.client.force_authenticate(user=self.free_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("not available on your current plan", str(response.data))

    def test_pro_tier_can_access_audit_logs(self):
        self.client.force_authenticate(user=self.pro_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
