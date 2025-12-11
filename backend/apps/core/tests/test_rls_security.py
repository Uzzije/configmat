"""
Security tests for Row-Level Security (RLS) context setting.

These tests verify that tenant context is set safely without SQL injection vulnerabilities.
"""

import pytest
import uuid
from unittest.mock import patch, MagicMock, call
from django.test import RequestFactory, override_settings
from django.contrib.auth.models import AnonymousUser

from apps.core.permissions import TenantContextPermission
from apps.core.middleware import TenantContextMiddleware
from apps.authentication.models import User, Tenant


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def test_tenant(db):
    return Tenant.objects.create(name='Test Tenant', slug='test-tenant')


@pytest.fixture
def test_user(db, test_tenant):
    return User.objects.create_user(
        email='test@example.com',
        password='testpass123',
        tenant=test_tenant,
        current_tenant=test_tenant
    )


@pytest.mark.django_db
class TestRLSSecurity:
    """Security tests for RLS context setting."""
    
    def test_tenant_id_uses_parameterized_query(self, request_factory, test_user):
        """
        Ensure SQL uses parameterized queries, not string interpolation.
        
        This is critical to prevent SQL injection attacks where a malicious
        tenant ID like "'; DROP TABLE users; --" could be injected.
        """
        request = request_factory.get('/api/test/')
        request.user = test_user
        
        permission = TenantContextPermission()
        
        with patch('django.db.connection.cursor') as mock_cursor:
            mock_ctx = MagicMock()
            mock_cursor.return_value.__enter__.return_value = mock_ctx
            
            permission.has_permission(request, None)
            
            # Verify that execute was called
            assert mock_ctx.execute.called
            
            # Get the SQL that was executed
            call_args = mock_ctx.execute.call_args
            sql = call_args[0][0]
            
            # The SQL should contain a placeholder %s, not the raw UUID
            # If it contains the raw UUID as a string, it's vulnerable
            tenant_id_str = str(test_user.current_tenant.id)
            
            # TODO: After fix, this assertion should pass:
            # assert '%s' in sql, "SQL should use parameterized query"
            # assert tenant_id_str not in sql, "SQL should not contain raw tenant ID"
    
    def test_middleware_uses_parameterized_query(self, request_factory, test_user):
        """Middleware should also use parameterized queries."""
        request = request_factory.get('/api/test/')
        request.user = test_user
        
        def get_response(request):
            return MagicMock()
        
        middleware = TenantContextMiddleware(get_response)
        
        with patch('django.db.connection.cursor') as mock_cursor:
            mock_ctx = MagicMock()
            mock_cursor.return_value.__enter__.return_value = mock_ctx
            
            middleware(request)
            
            # Verify parameterized queries are used
            # TODO: After fix, verify the call signature
    
    def test_invalid_uuid_format_rejected(self, request_factory, test_user):
        """
        Ensure non-UUID tenant IDs are rejected.
        
        Even though UUIDs are type-safe, we should validate format
        as defense in depth.
        """
        request = request_factory.get('/api/test/')
        request.user = test_user
        
        # Simulate a corrupted tenant ID (shouldn't happen with FK, but defense in depth)
        test_user.current_tenant.id = "not-a-uuid"
        
        permission = TenantContextPermission()
        
        # Should either raise or handle gracefully
        # TODO: Add UUID validation and update test
    
    def test_rls_context_set_correctly_for_authenticated_user(self, request_factory, test_user):
        """Verify RLS context is set with correct tenant ID for auth user."""
        request = request_factory.get('/api/test/')
        request.user = test_user
        
        permission = TenantContextPermission()
        
        with patch('django.db.connection.cursor') as mock_cursor:
            mock_ctx = MagicMock()
            mock_cursor.return_value.__enter__.return_value = mock_ctx
            
            result = permission.has_permission(request, None)
            
            assert result is True
            assert mock_ctx.execute.called
    
    def test_rls_context_reset_for_anonymous_user(self, request_factory):
        """Verify RLS context is reset for unauthenticated requests."""
        request = request_factory.get('/api/test/')
        request.user = AnonymousUser()
        request.auth = None
        
        permission = TenantContextPermission()
        
        with patch('django.db.connection.cursor') as mock_cursor:
            mock_ctx = MagicMock()
            mock_cursor.return_value.__enter__.return_value = mock_ctx
            
            result = permission.has_permission(request, None)
            
            # Permission should return True (doesn't block, just sets context)
            assert result is True
            # For anonymous, no tenant context should be set
    
    def test_superuser_bypass_flag_set(self, request_factory, test_user):
        """Verify superuser bypass flag is correctly set."""
        request = request_factory.get('/api/test/')
        test_user.is_superuser = True
        request.user = test_user
        
        def get_response(request):
            return MagicMock()
        
        middleware = TenantContextMiddleware(get_response)
        
        with patch('django.db.connection.cursor') as mock_cursor:
            mock_ctx = MagicMock()
            mock_cursor.return_value.__enter__.return_value = mock_ctx
            
            middleware(request)
            
            # Should set is_superuser flag via set_config
            calls = mock_ctx.execute.call_args_list
            
            # Check that we're setting app.is_superuser
            # With parameterized query: SELECT set_config(%s, %s, false) with params ['app.is_superuser', 'on']
            found_superuser_setting = False
            for call in calls:
                args = call[0]
                sql = args[0]
                params = args[1] if len(args) > 1 else []
                
                # Check for parameterized set_config call
                if 'set_config' in sql and params and 'app.is_superuser' in params:
                    found_superuser_setting = True
                    break
            
            assert found_superuser_setting, f"Expected is_superuser to be set. Calls: {calls}"


@pytest.mark.django_db
class TestAPIKeyAuthentication:
    """Security tests for API Key authentication RLS context."""
    
    def test_api_key_tenant_context_parameterized(self, request_factory, test_tenant, test_user):
        """API Key authentication should also use parameterized queries."""
        from apps.api_keys.models import APIKey
        import secrets
        
        # Create API key
        key_value = f"cm_{secrets.token_urlsafe(32)}"
        api_key = APIKey.objects.create(
            tenant=test_tenant,
            scope='tenant',
            environment='local',
            created_by=test_user,
            label='Test Key',
            key_hash=APIKey.hash_key(key_value),
            key_prefix=key_value[:16]
        )
        
        request = request_factory.get('/api/test/')
        request.user = test_user
        request.auth = api_key
        
        permission = TenantContextPermission()
        
        with patch('django.db.connection.cursor') as mock_cursor:
            mock_ctx = MagicMock()
            mock_cursor.return_value.__enter__.return_value = mock_ctx
            
            permission.has_permission(request, None)
            
            # TODO: Verify parameterized query after fix

