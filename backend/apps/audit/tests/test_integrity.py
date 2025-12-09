from django.test import TestCase
from apps.audit.models import ActivityLog
from apps.authentication.models import Tenant

class AuditIntegrityTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='Test Tenant', slug='test-tenant')

    def test_merkle_chain_creation(self):
        # 1. Create first log (Genesis)
        log1 = ActivityLog.objects.create(
            tenant=self.tenant,
            action='create_asset',
            target='Asset A',
            details={'foo': 'bar'}
        )
        
        # Verify genesis previous hash
        self.assertEqual(log1.previous_hash, '0' * 64)
        self.assertTrue(log1.hash)

        # 2. Create second log
        log2 = ActivityLog.objects.create(
            tenant=self.tenant,
            action='update_asset',
            target='Asset A',
            details={'foo': 'baz'}
        )
        
        # Verify linking
        self.assertEqual(log2.previous_hash, log1.hash)
        self.assertNotEqual(log2.hash, log1.hash)

        # 3. Create third log
        log3 = ActivityLog.objects.create(
            tenant=self.tenant,
            action='delete_asset',
            target='Asset A'
        )
        
        self.assertEqual(log3.previous_hash, log2.hash)

    def test_immutability(self):
        log = ActivityLog.objects.create(
            tenant=self.tenant,
            action='test',
            target='target'
        )
        
        # Try to update
        log.action = 'tampered'
        with self.assertRaisesMessage(ValueError, "ActivityLog is immutable"):
            log.save() 
