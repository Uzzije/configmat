# Environment Variables Setup

This document describes all environment variables required for ConfigMat backend.

## Quick Start (Development)

Create a `.env` file in the backend directory:

```bash
cd app/backend
cp docs/env.template .env
# Edit .env with your values
```

## Environment Variables Reference

### Django Core Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes (prod) | dev key | Django secret key. Generate with: `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'` |
| `DEBUG` | No | `True` | Set to `False` in production |
| `ALLOWED_HOSTS` | Yes (prod) | `localhost,127.0.0.1` | Comma-separated list of allowed hosts |

### Database

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DB_NAME` | No | `configmat` | PostgreSQL database name |
| `DB_USER` | No | `configmat` | Database user |
| `DB_PASSWORD` | Yes (prod) | dev password | Database password |
| `DB_HOST` | No | `localhost` | Database host |
| `DB_PORT` | No | `5432` | Database port |

### Encryption (Critical Security)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENCRYPTION_KEY` | **Yes (prod)** | None | 32-byte hex key for encrypting secrets. Generate with: `python -c 'import secrets; print(secrets.token_hex(32))'` |

⚠️ **WARNING**: 
- The `ENCRYPTION_KEY` protects all encrypted secrets in the database
- Never commit this value to version control
- Back up this key securely - losing it means losing access to encrypted data
- In production, use a secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.)
- If not set in DEBUG mode, falls back to SECRET_KEY (insecure, dev only)
- **If not set in production (DEBUG=False), the app will refuse to start**

### Redis / Cache

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection URL |

### CORS

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CORS_ALLOWED_ORIGINS` | No | `http://localhost:5173,http://localhost:3000` | Comma-separated allowed origins |

### External Services

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BREVO_API_KEY` | No | None | Brevo/Sendinblue API key for emails |
| `FRONTEND_URL` | No | `http://localhost:5173` | Frontend URL for email links |
| `OPENAI_API_KEY` | No | None | OpenAI API key for chat features |

### Rate Limiting (After Implementation)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RATE_LIMIT_ANON` | No | `100/hour` | Anonymous request limit |
| `RATE_LIMIT_USER` | No | `1000/hour` | Authenticated user limit |
| `RATE_LIMIT_API_KEY` | No | `10000/hour` | API key request limit |

### Logging (After Implementation)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LOG_LEVEL` | No | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FORMAT` | No | `json` | Log format (json, text) |

## Template

Copy this template to `.env`:

```bash
# =============================================================================
# DJANGO CORE SETTINGS
# =============================================================================
SECRET_KEY=django-insecure-dev-key-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# =============================================================================
# DATABASE
# =============================================================================
DB_NAME=configmat
DB_USER=configmat
DB_PASSWORD=configmat_dev_password
DB_HOST=localhost
DB_PORT=5432

# =============================================================================
# ENCRYPTION (REQUIRED IN PRODUCTION)
# =============================================================================
# Generate with: python -c 'import secrets; print(secrets.token_hex(32))'
ENCRYPTION_KEY=

# =============================================================================
# REDIS / CACHE
# =============================================================================
REDIS_URL=redis://localhost:6379/0

# =============================================================================
# CORS
# =============================================================================
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# =============================================================================
# EXTERNAL SERVICES
# =============================================================================
BREVO_API_KEY=
FRONTEND_URL=http://localhost:5173
OPENAI_API_KEY=
```

## Production Checklist

Before deploying to production, ensure:

- [ ] `SECRET_KEY` is set to a unique, random value
- [ ] `DEBUG` is set to `False`
- [ ] `ENCRYPTION_KEY` is set to a secure random value
- [ ] `ALLOWED_HOSTS` includes your domain(s)
- [ ] Database credentials are secure and not defaults
- [ ] Redis is configured for cache and task queue
- [ ] HTTPS is enforced (handle at load balancer/proxy level)
- [ ] CORS origins are restricted to your frontend domain(s)
- [ ] All API keys are production values (not dev/test)

## Secrets Management (Production)

For production deployments, consider using:

1. **AWS Secrets Manager** - Native AWS integration
2. **HashiCorp Vault** - Self-hosted or cloud secrets management
3. **Google Secret Manager** - GCP native solution
4. **Azure Key Vault** - Azure native solution

Example with AWS Secrets Manager:

```python
# In settings.py
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

if not DEBUG:
    secrets = get_secret('configmat/production')
    ENCRYPTION_KEY = secrets['encryption_key']
    # etc.
```

