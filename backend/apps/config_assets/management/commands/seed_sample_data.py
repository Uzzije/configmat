"""
Management command to seed sample data for testing.

Creates a test organization with sample configuration if it doesn't exist.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.authentication.models import User, Tenant
from apps.config_assets.models import ConfigAsset, ConfigValue
from apps.api_keys.models import APIKey
import secrets


class Command(BaseCommand):
    help = 'Seed sample data for testing ConfigMat SDKs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--org',
            type=str,
            default='final-test-org',
            help='Organization slug (default: final-test-org)'
        )
        parser.add_argument(
            '--email',
            type=str,
            default='jane.smith@example.com',
            help='User email (default: jane.smith@example.com)'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        org_slug = options['org']
        user_email = options['email']

        self.stdout.write(self.style.SUCCESS('🌱 Seeding sample data...'))
        self.stdout.write(f'   Organization: {org_slug}')
        self.stdout.write(f'   User: {user_email}')
        self.stdout.write('')

        # Get or create user and tenant
        try:
            user = User.objects.get(email=user_email)
            tenant = user.tenant
            self.stdout.write(self.style.SUCCESS(f'✅ Found existing user: {user.email}'))
            self.stdout.write(f'   Tenant: {tenant.name} ({tenant.slug})')
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ User {user_email} not found'))
            self.stdout.write('   Please create the user first or use --email with an existing user')
            return

        # Create or get test asset
        asset, created = ConfigAsset.objects.get_or_create(
            tenant=tenant,
            slug='test-asset',
            defaults={
                'name': 'Test Asset',
                'description': 'Sample asset for SDK testing',
                'created_by': user
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ Created asset: {asset.name}'))
        else:
            self.stdout.write(f'   Found existing asset: {asset.name}')

        # Sample configuration data
        sample_configs = {
            'app_settings': {
                'retries': '3',
                'theme': 'dark',
                'timeout': '30',
                'debug': 'true'
            },
            'database_config': {
                'host': 'localhost',
                'port': 5432,
                'name': 'configmat_db',
                'ssl': False,
                'pool': {
                    'min': 2,
                    'max': 10,
                    'idle_timeout': 30000
                }
            },
            'stripe_config': {
                'api_key': 'sk_test_51234567890abcdef',
                'webhook_secret': 'whsec_test_1234567890abcdef',
                'connect_enabled': True,
                'currency': 'usd'
            },
            'feature_flags': {
                'new_checkout': True,
                'beta_features': False,
                'maintenance_mode': False,
                'dark_mode': True
            },
            'email_config': {
                'provider': 'sendgrid',
                'api_key': 'SG.test_key_1234567890',
                'from_email': 'noreply@example.com',
                'from_name': 'ConfigMat'
            }
        }

        # Create or update config value for local environment
        config_value, created = ConfigValue.objects.get_or_create(
            asset=asset,
            environment='local',
            defaults={
                'values': sample_configs,
                'created_by': user
            }
        )

        if not created:
            # Update existing config
            config_value.values = sample_configs
            config_value.save()
            self.stdout.write(f'   Updated configuration for environment: local')
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ Created configuration for environment: local'))

        self.stdout.write(f'   Config objects: {list(sample_configs.keys())}')

        # Create or get API key
        api_keys = APIKey.objects.filter(
            tenant=tenant,
            created_by=user,
            revoked=False
        ).order_by('-created_at')

        if api_keys.exists():
            api_key = api_keys.first()
            self.stdout.write(f'   Found existing API key: {api_key.key_prefix}...')
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('⚠️  Note: Cannot retrieve the full API key (it\'s hashed)'))
            self.stdout.write('   If you need a new key, create one via the admin panel or API')
        else:
            # Generate new API key
            org_hash = APIKey.generate_org_hash(tenant.slug)
            random_part = secrets.token_urlsafe(16)
            raw_key = f"cm_{org_hash}_{random_part}"
            key_hash = APIKey.hash_key(raw_key)

            api_key = APIKey.objects.create(
                tenant=tenant,
                scope='tenant',
                environment='local',
                created_by=user,
                key_hash=key_hash,
                key_prefix=raw_key[:16],
                label='SDK Test Key - Auto Generated'
            )

            self.stdout.write(self.style.SUCCESS('✅ Created new API key'))
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('📋 API Key (save this, it won\'t be shown again):'))
            self.stdout.write(f'   {raw_key}')

        # Print summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('🎉 Sample data seeded successfully!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        self.stdout.write('📊 Summary:')
        self.stdout.write(f'   Organization: {tenant.name} ({tenant.slug})')
        self.stdout.write(f'   Asset: {asset.slug}')
        self.stdout.write(f'   Environment: local')
        self.stdout.write(f'   Config Objects: {len(sample_configs)}')
        self.stdout.write('')
        self.stdout.write('🔧 Use these credentials in your SDK:')
        self.stdout.write(f'   CONFIGMAT_ORG="{tenant.slug}"')
        self.stdout.write(f'   CONFIGMAT_ASSET="test-asset"')
        self.stdout.write(f'   CONFIGMAT_BASE_URL="http://127.0.0.1:8000"')
        if not api_keys.exists():
            self.stdout.write(f'   CONFIGMAT_API_KEY="{raw_key}"')
        else:
            self.stdout.write(f'   CONFIGMAT_API_KEY="<use existing key or create new one>"')
        self.stdout.write('')
