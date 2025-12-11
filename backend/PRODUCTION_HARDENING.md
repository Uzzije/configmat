# Production Hardening Game Plan

> **Status**: Draft  
> **Last Updated**: December 10, 2025  
> **Estimated Effort**: 2-3 weeks  
> **Priority Legend**: P0 (Critical/Security), P1 (High), P2 (Medium)

---

## Executive Summary

This document outlines the game plan to bring ConfigMat's backend from MVP-quality to production-grade. The assessment identified 10 key areas requiring attention, with 3 critical security/data-integrity issues that must be addressed before any production deployment.

---

## Phase 1: Critical Security & Data Integrity (P0)
**Timeline: Week 1 (Days 1-5)**

### 1.1 SQL Injection Prevention in RLS Context Setting

**Problem**: Raw f-string SQL formatting in permission and middleware classes.

**Files to Modify**:
- `apps/core/permissions.py`
- `apps/core/middleware.py`

**Current Code** (`permissions.py:12-13`):
```python
cursor.execute(f"SET app.current_tenant = '{request.user.current_tenant.id}';")
```

**Target Code**:
```python
cursor.execute("SET app.current_tenant = %s;", [str(request.user.current_tenant.id)])
```

**Tasks**:
- [ ] Update `TenantContextPermission.has_permission()` to use parameterized queries
- [ ] Update `TenantContextMiddleware.__call__()` to use parameterized queries
- [ ] Add input validation for tenant IDs (UUID format check)

**Test Plan**:
```python
# apps/core/tests/test_rls_security.py

import pytest
from unittest.mock import patch, MagicMock
from django.test import RequestFactory
from apps.core.permissions import TenantContextPermission
from apps.core.middleware import TenantContextMiddleware

class TestRLSSecurity:
    """Security tests for RLS context setting."""
    
    def test_tenant_id_is_parameterized_not_interpolated(self):
        """Ensure SQL uses parameterized queries, not string interpolation."""
        # Mock a malicious tenant ID attempt
        with patch('django.db.connection.cursor') as mock_cursor:
            mock_ctx = MagicMock()
            mock_cursor.return_value.__enter__.return_value = mock_ctx
            
            # The actual execute call should use %s placeholder
            # If vulnerable, attacker could inject: "'; DROP TABLE users; --"
            # Test that the query uses parameterization
            
    def test_invalid_uuid_tenant_id_rejected(self):
        """Ensure non-UUID tenant IDs are rejected."""
        pass
        
    def test_rls_context_set_correctly_for_authenticated_user(self):
        """Verify RLS context is set with correct tenant ID."""
        pass
        
    def test_rls_context_reset_for_anonymous_user(self):
        """Verify RLS context is reset for unauthenticated requests."""
        pass
```

---

### 1.2 Atomic Transactions for Multi-Write Operations

**Problem**: `promote_asset()` and `rollback_to_version()` perform multiple DB writes without atomicity. Partial failures leave inconsistent state.

**Files to Modify**:
- `apps/config_assets/services.py`

**Current Code**:
```python
def promote_asset(asset_id, from_env, to_env, user_id):
    # Multiple .create(), .delete() calls without transaction
```

**Target Code**:
```python
from django.db import transaction

@transaction.atomic
def promote_asset(asset_id, from_env, to_env, user_id):
    # All operations now in single transaction
```

**Tasks**:
- [ ] Add `@transaction.atomic` decorator to `promote_asset()`
- [ ] Add `@transaction.atomic` decorator to `rollback_to_version()`
- [ ] Add `@transaction.atomic` decorator to `create_config_version()`
- [ ] Review all service functions for multi-write patterns
- [ ] Add `select_for_update()` where concurrent access is possible

**Test Plan**:
```python
# apps/config_assets/tests/test_transaction_safety.py

import pytest
from django.db import transaction
from unittest.mock import patch
from apps.config_assets.services import promote_asset, rollback_to_version
from apps.config_assets.models import ConfigAsset, ConfigValue

@pytest.mark.django_db(transaction=True)
class TestTransactionSafety:
    """Tests for atomic transaction behavior."""
    
    def test_promote_asset_rollback_on_failure(self, test_asset, test_config_values):
        """Ensure partial promotion is rolled back on error."""
        initial_count = ConfigValue.objects.count()
        
        with patch('apps.config_assets.services.create_config_version') as mock:
            mock.side_effect = Exception("Simulated failure")
            
            with pytest.raises(Exception):
                promote_asset(test_asset.id, 'local', 'stage', user_id)
        
        # Count should be unchanged (rollback occurred)
        assert ConfigValue.objects.count() == initial_count
    
    def test_rollback_to_version_atomic(self, test_version):
        """Ensure rollback is atomic."""
        pass
        
    def test_concurrent_promote_uses_locking(self, test_asset):
        """Ensure concurrent promotions don't corrupt data."""
        # Use threading to simulate concurrent access
        pass
```

---

### 1.3 Fail-Loud Encryption Key Configuration

**Problem**: Missing `ENCRYPTION_KEY` silently falls back to `SECRET_KEY`, which is a severe security risk in production.

**Files to Modify**:
- `apps/core/encryption.py`
- `configmat/settings.py`

**Current Code** (`encryption.py:26-33`):
```python
key_hex = getattr(settings, 'ENCRYPTION_KEY', None)
if not key_hex:
    # Fallback to SECRET_KEY (Insecure for prod)
    key_digest = hashlib.sha256(key_material).digest()
```

**Target Code**:
```python
from django.core.exceptions import ImproperlyConfigured

key_hex = getattr(settings, 'ENCRYPTION_KEY', None)
if not key_hex:
    if not settings.DEBUG:
        raise ImproperlyConfigured(
            "ENCRYPTION_KEY must be set in production. "
            "Generate with: python -c 'import secrets; print(secrets.token_hex(32))'"
        )
    # Only allow fallback in DEBUG mode
    import warnings
    warnings.warn("Using SECRET_KEY as encryption key. DO NOT USE IN PRODUCTION.", UserWarning)
    key_digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
```

**Tasks**:
- [ ] Add `ImproperlyConfigured` exception for missing `ENCRYPTION_KEY` in production
- [ ] Add development warning when using fallback
- [ ] Add `ENCRYPTION_KEY` to `.env.example` with generation instructions
- [ ] Update `settings.py` to document the setting
- [ ] Add startup check in `apps/core/apps.py` ready() hook

**Test Plan**:
```python
# apps/core/tests/test_encryption_config.py

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from apps.core.encryption import KeyManager

class TestEncryptionConfiguration:
    """Tests for encryption key configuration safety."""
    
    @override_settings(DEBUG=False, ENCRYPTION_KEY=None)
    def test_missing_key_in_production_raises_error(self):
        """Production without ENCRYPTION_KEY must fail loudly."""
        KeyManager._kek = None  # Reset cached key
        
        with pytest.raises(ImproperlyConfigured) as exc_info:
            KeyManager.get_kek()
        
        assert "ENCRYPTION_KEY must be set" in str(exc_info.value)
    
    @override_settings(DEBUG=True, ENCRYPTION_KEY=None)
    def test_missing_key_in_debug_warns(self):
        """Debug mode should warn but not fail."""
        KeyManager._kek = None
        
        with pytest.warns(UserWarning, match="DO NOT USE IN PRODUCTION"):
            key = KeyManager.get_kek()
        
        assert key is not None
        assert len(key) == 32
    
    @override_settings(ENCRYPTION_KEY='a' * 64)  # 32 bytes hex
    def test_valid_hex_key_works(self):
        """Valid hex ENCRYPTION_KEY should work."""
        KeyManager._kek = None
        key = KeyManager.get_kek()
        assert len(key) == 32
```

---

## Phase 2: Performance & Reliability (P1)
**Timeline: Week 2 (Days 6-10)**

### 2.1 N+1 Query Optimization

**Problem**: Config resolution queries each object's values in a loop.

**Files to Modify**:
- `apps/config_assets/services.py`

**Current Code**:
```python
config_objects = asset.config_objects.all()
for obj in config_objects:
    values = obj.values.filter(environment=environment)  # N+1!
```

**Target Code**:
```python
from django.db.models import Prefetch

config_objects = asset.config_objects.prefetch_related(
    Prefetch(
        'values',
        queryset=ConfigValue.objects.filter(environment=environment),
        to_attr='env_values'
    )
).all()

for obj in config_objects:
    values = obj.env_values  # Pre-fetched!
```

**Tasks**:
- [ ] Add `prefetch_related` to `get_resolved_config()`
- [ ] Add `select_related` for tenant lookups in views
- [ ] Install and configure `django-debug-toolbar` for development
- [ ] Add query count assertions to critical path tests

**Test Plan**:
```python
# apps/config_assets/tests/test_query_optimization.py

import pytest
from django.test.utils import CaptureQueriesContext
from django.db import connection
from apps.config_assets.services import get_resolved_config

@pytest.mark.django_db
class TestQueryOptimization:
    """Tests for query count optimization."""
    
    def test_get_resolved_config_query_count(self, asset_with_10_objects):
        """Config resolution should use constant query count."""
        with CaptureQueriesContext(connection) as context:
            get_resolved_config(
                asset_slug=asset_with_10_objects.slug,
                environment='local',
                tenant_id=asset_with_10_objects.tenant_id
            )
        
        # Should be ~3 queries (asset, objects with prefetch, cache set)
        # NOT 1 + N (where N = number of objects)
        assert len(context) <= 5, f"Too many queries: {len(context)}"
    
    def test_asset_list_query_count(self, tenant_with_50_assets, authenticated_client):
        """Asset list endpoint should have bounded queries."""
        with CaptureQueriesContext(connection) as context:
            response = authenticated_client.get('/api/assets/')
        
        assert len(context) <= 10
```

---

### 2.2 API Rate Limiting

**Problem**: No throttling configured; API vulnerable to abuse.

**Files to Modify**:
- `configmat/settings.py`
- New file: `apps/core/throttling.py`

**Target Configuration**:
```python
# settings.py
REST_FRAMEWORK = {
    # ... existing config ...
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "apps.core.throttling.APIKeyRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        "api_key": "10000/hour",
        "api_key_burst": "100/minute",
    },
}
```

**Tasks**:
- [ ] Add throttle classes to DRF settings
- [ ] Create custom `APIKeyRateThrottle` for SDK access
- [ ] Add Redis-backed throttling for distributed deployments
- [ ] Add `X-RateLimit-*` headers to responses
- [ ] Create throttle bypass for health checks

**Test Plan**:
```python
# apps/core/tests/test_rate_limiting.py

import pytest
from rest_framework.test import APIClient
from django.core.cache import cache

@pytest.mark.django_db
class TestRateLimiting:
    """Tests for API rate limiting."""
    
    def setup_method(self):
        cache.clear()
    
    def test_anonymous_rate_limit_enforced(self):
        """Anonymous requests should be rate limited."""
        client = APIClient()
        
        # Make requests up to limit
        for i in range(100):
            response = client.get('/api/v1/health/')
            assert response.status_code == 200
        
        # Next request should be throttled
        response = client.get('/api/v1/health/')
        assert response.status_code == 429
        assert 'Retry-After' in response.headers
    
    def test_api_key_has_higher_limit(self, test_api_key):
        """API key requests should have higher limits."""
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=test_api_key.key_value)
        
        # Should allow more than anonymous limit
        for i in range(150):
            response = client.get('/api/v1/assets/test/values/')
        
        # Should still work (under 10000/hour)
        assert response.status_code in [200, 404]
    
    def test_rate_limit_headers_present(self, authenticated_client):
        """Responses should include rate limit headers."""
        response = authenticated_client.get('/api/assets/')
        
        assert 'X-RateLimit-Limit' in response.headers
        assert 'X-RateLimit-Remaining' in response.headers
```

---

### 2.3 Structured Logging with Request Tracing

**Problem**: Using `print()` statements; no structured logging or request tracing.

**Files to Modify**:
- `configmat/settings.py`
- `apps/core/middleware.py` (add request ID middleware)
- All files using `print()` for logging

**New Dependencies**:
```
django-structlog>=6.0
python-json-logger>=2.0
```

**Target Configuration**:
```python
# settings.py
import structlog

MIDDLEWARE = [
    # ... existing ...
    "django_structlog.middlewares.RequestMiddleware",  # Add before TenantContext
    "apps.core.middleware.TenantContextMiddleware",
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO"},
        "apps": {"handlers": ["console"], "level": "DEBUG"},
    },
}

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
```

**Tasks**:
- [ ] Install `django-structlog` and `python-json-logger`
- [ ] Configure structured logging in settings
- [ ] Replace all `print()` calls with proper logger calls
- [ ] Add request ID middleware
- [ ] Add tenant context to all log entries
- [ ] Add performance timing to critical paths

**Test Plan**:
```python
# apps/core/tests/test_logging.py

import pytest
import structlog
from io import StringIO
import json

class TestStructuredLogging:
    """Tests for structured logging."""
    
    def test_request_id_in_logs(self, authenticated_client, caplog):
        """All log entries should include request_id."""
        response = authenticated_client.get('/api/assets/')
        
        # Check that logs contain request_id
        for record in caplog.records:
            assert hasattr(record, 'request_id') or 'request_id' in str(record.msg)
    
    def test_tenant_context_in_logs(self, authenticated_client, caplog):
        """Logs should include tenant context."""
        response = authenticated_client.get('/api/assets/')
        
        # Verify tenant appears in structured log
        pass
    
    def test_cache_error_logged_not_printed(self, mocker):
        """Cache errors should use logger, not print()."""
        mock_logger = mocker.patch('apps.config_assets.signals.logger')
        
        # Trigger cache error
        # Verify logger.error was called, not print()
```

---

### 2.4 Merkle Chain Race Condition Fix

**Problem**: Concurrent audit log creation can break the chain due to race conditions.

**Files to Modify**:
- `apps/audit/models.py`
- New file: `apps/audit/tasks.py` (for async queue approach)

**Option A: Database Locking** (simpler, lower throughput):
```python
def calculate_hash(self):
    from django.db import transaction
    
    with transaction.atomic():
        # Lock tenant's audit logs for update
        last_log = (
            ActivityLog.objects
            .select_for_update()
            .filter(tenant=self.tenant)
            .order_by('-created_at')
            .first()
        )
        # ... rest of hash calculation
```

**Option B: Serialized Queue** (higher throughput, requires Dramatiq):
```python
# apps/audit/tasks.py
import dramatiq
from .models import ActivityLog

@dramatiq.actor(queue_name="audit")
def create_audit_log(tenant_id, user_id, action, target, details):
    """Serialized audit log creation via queue."""
    ActivityLog.objects.create(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        target=target,
        details=details
    )
```

**Tasks**:
- [ ] Choose implementation approach (locking vs queue)
- [ ] Implement selected approach
- [ ] Add integration test for concurrent writes
- [ ] Add chain verification utility function
- [ ] Document the tradeoffs in code comments

**Test Plan**:
```python
# apps/audit/tests/test_merkle_concurrency.py

import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed
from apps.audit.models import ActivityLog

@pytest.mark.django_db(transaction=True)
class TestMerkleConcurrency:
    """Tests for Merkle chain integrity under concurrency."""
    
    def test_concurrent_log_creation_maintains_chain(self, test_tenant, test_user):
        """Chain should remain valid under concurrent writes."""
        def create_log(i):
            return ActivityLog.objects.create(
                tenant=test_tenant,
                user=test_user,
                action=f'action_{i}',
                target=f'target_{i}'
            )
        
        # Create 50 logs concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_log, i) for i in range(50)]
            logs = [f.result() for f in as_completed(futures)]
        
        # Verify chain integrity
        all_logs = ActivityLog.objects.filter(tenant=test_tenant).order_by('created_at')
        
        prev_hash = '0' * 64
        for log in all_logs:
            assert log.previous_hash == prev_hash, f"Chain broken at {log.id}"
            prev_hash = log.hash
    
    def test_chain_verification_utility(self, test_tenant):
        """Utility should detect tampered chains."""
        # Create valid chain
        # Manually tamper with middle entry
        # Verify detection
        pass
```

---

## Phase 3: Operational Excellence (P2)
**Timeline: Week 3 (Days 11-15)**

### 3.1 Standardized Error Response Schema

**Problem**: Inconsistent error responses make client error handling difficult.

**Files to Modify**:
- New file: `apps/core/exceptions.py`
- New file: `apps/core/exception_handlers.py`
- `configmat/settings.py`

**Target Schema** (RFC 7807 inspired):
```json
{
  "error": {
    "code": "ASSET_NOT_FOUND",
    "message": "The requested asset does not exist.",
    "details": {
      "asset_slug": "nonexistent",
      "tenant": "acme-corp"
    },
    "request_id": "req_abc123",
    "documentation_url": "https://docs.configmat.io/errors/ASSET_NOT_FOUND"
  }
}
```

**Tasks**:
- [ ] Create custom exception classes in `apps/core/exceptions.py`
- [ ] Create custom exception handler
- [ ] Update all views to use new exception pattern
- [ ] Add error code documentation
- [ ] Ensure 500 errors don't leak internal details

**Test Plan**:
```python
# apps/core/tests/test_error_responses.py

import pytest
from rest_framework.test import APIClient

@pytest.mark.django_db
class TestErrorResponses:
    """Tests for standardized error responses."""
    
    def test_404_has_error_code(self, authenticated_client):
        """404 responses should include error code."""
        response = authenticated_client.get('/api/assets/nonexistent/')
        
        assert response.status_code == 404
        assert 'error' in response.data
        assert 'code' in response.data['error']
        assert response.data['error']['code'] == 'ASSET_NOT_FOUND'
    
    def test_validation_error_format(self, authenticated_client):
        """Validation errors should use standard format."""
        response = authenticated_client.post('/api/assets/', {})
        
        assert response.status_code == 400
        assert 'error' in response.data
        assert 'code' in response.data['error']
    
    def test_500_does_not_leak_details(self, authenticated_client, mocker):
        """Internal errors should not expose stack traces."""
        mocker.patch(
            'apps.config_assets.views.ConfigAssetViewSet.get_queryset',
            side_effect=Exception("Database connection failed")
        )
        
        response = authenticated_client.get('/api/assets/')
        
        assert response.status_code == 500
        assert 'Database connection' not in str(response.data)
        assert response.data['error']['code'] == 'INTERNAL_ERROR'
```

---

### 3.2 Database Connection Pooling

**Problem**: Using Django's default per-request connections; not optimal for high load.

**Files to Modify**:
- `requirements.txt`
- `configmat/settings.py`
- `docker-compose.yml` (add pgbouncer)

**Option A: django-db-connection-pool**:
```python
# settings.py
DATABASES = {
    "default": {
        "ENGINE": "dj_db_conn_pool.backends.postgresql",
        "POOL_OPTIONS": {
            "POOL_SIZE": 10,
            "MAX_OVERFLOW": 20,
            "RECYCLE": 300,
        },
        # ... rest of config
    }
}
```

**Option B: External PgBouncer** (recommended for production):
```yaml
# docker-compose.yml
services:
  pgbouncer:
    image: edoburu/pgbouncer:1.21.0
    environment:
      DATABASE_URL: postgres://user:pass@db:5432/configmat
      POOL_MODE: transaction
      MAX_CLIENT_CONN: 1000
      DEFAULT_POOL_SIZE: 20
```

**Tasks**:
- [ ] Choose pooling strategy (in-app vs external)
- [ ] Configure connection pooling
- [ ] Add health check for pool status
- [ ] Load test with connection pool
- [ ] Document connection limits

---

### 3.3 Health Check Enhancement

**Files to Modify**:
- `apps/api/v1/views/health.py`

**Target Implementation**:
```python
class DetailedHealthView(APIView):
    """
    Comprehensive health check for monitoring systems.
    
    GET /api/v1/health/detailed/
    """
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []  # Don't throttle health checks
    
    def get(self, request):
        checks = {
            "database": self._check_database(),
            "cache": self._check_cache(),
            "encryption": self._check_encryption(),
        }
        
        all_healthy = all(c["status"] == "healthy" for c in checks.values())
        
        return Response(
            {
                "status": "healthy" if all_healthy else "degraded",
                "checks": checks,
                "version": settings.APP_VERSION,
                "timestamp": timezone.now().isoformat(),
            },
            status=200 if all_healthy else 503
        )
```

---

## Test Coverage Requirements

### Minimum Coverage Targets

| Module | Current (est.) | Target |
|--------|---------------|--------|
| `apps/core/` | ~60% | 90% |
| `apps/config_assets/services.py` | ~70% | 95% |
| `apps/audit/` | ~50% | 85% |
| `apps/api/v1/` | ~75% | 90% |
| Overall | ~65% | 85% |

### Running Tests

```bash
# Run all tests with coverage
pytest --cov=apps --cov-report=html --cov-report=term-missing

# Run specific test categories
pytest -m "security"      # Security tests
pytest -m "performance"   # Performance tests  
pytest -m "integration"   # Integration tests

# Run with parallel execution
pytest -n auto
```

### CI/CD Integration

```yaml
# .github/workflows/test.yml
test:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Run Tests
      run: |
        pytest --cov=apps --cov-fail-under=85
    - name: Security Scan
      run: |
        bandit -r apps/
        safety check
```

---

## Definition of Done

A task is complete when:

1. ✅ Code changes implemented and reviewed
2. ✅ Unit tests written and passing
3. ✅ Integration tests written and passing
4. ✅ Documentation updated (if applicable)
5. ✅ No new linting errors
6. ✅ Security scan passes (bandit, safety)
7. ✅ Coverage threshold met (85%+)

---

## Appendix A: New Dependencies

```
# requirements.txt additions

# Logging
django-structlog>=6.0.0
python-json-logger>=2.0.0

# Database
dj-database-url>=2.1.0
django-db-connection-pool>=1.2.0  # If using in-app pooling

# Security
bandit>=1.7.0
safety>=2.3.0

# Testing
pytest-xdist>=3.5.0  # Parallel test execution
pytest-mock>=3.12.0
factory-boy>=3.3.0   # Better test fixtures
```

---

## Appendix B: Environment Variables

```bash
# .env.example additions

# REQUIRED in production
ENCRYPTION_KEY=  # Generate: python -c 'import secrets; print(secrets.token_hex(32))'

# Rate Limiting
RATE_LIMIT_ANON=100/hour
RATE_LIMIT_USER=1000/hour
RATE_LIMIT_API_KEY=10000/hour

# Connection Pooling
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_RECYCLE=300

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## Changelog

| Date | Author | Changes |
|------|--------|---------|
| 2024-12-10 | System | Initial document created |


