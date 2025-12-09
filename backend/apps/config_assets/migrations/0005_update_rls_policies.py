from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('config_assets', '0004_configvalue_value_encrypted_encryptionkey_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            -- Drop old policies
            DROP POLICY IF EXISTS tenant_isolation_assets ON config_assets;
            DROP POLICY IF EXISTS tenant_isolation_objects ON config_objects;
            DROP POLICY IF EXISTS tenant_isolation_values ON config_values;
            DROP POLICY IF EXISTS tenant_isolation_versions ON config_versions;

            -- Re-create policies with Superuser Bypass
            -- Checks if 'app.is_superuser' is set to 'on'. 
            -- Note: We cast current_setting to text to compare with 'on'. 
            -- current_setting(..., true) returns null if not set, so coalescing or checking null is needed implicitly by the OR.

            CREATE POLICY tenant_isolation_assets ON config_assets
                USING (
                    current_setting('app.is_superuser', true) = 'on' 
                    OR 
                    tenant_id = current_setting('app.current_tenant', true)::uuid
                );

            CREATE POLICY tenant_isolation_objects ON config_objects
                USING (
                    current_setting('app.is_superuser', true) = 'on'
                    OR
                    asset_id IN (SELECT id FROM config_assets)
                );

            CREATE POLICY tenant_isolation_values ON config_values
                USING (
                    current_setting('app.is_superuser', true) = 'on'
                    OR
                    config_object_id IN (SELECT id FROM config_objects)
                );

            CREATE POLICY tenant_isolation_versions ON config_versions
                USING (
                    current_setting('app.is_superuser', true) = 'on'
                    OR
                    config_object_id IN (SELECT id FROM config_objects)
                );
            """,
            reverse_sql="""
            -- Revert to strict policies (without superuser bypass)
            DROP POLICY IF EXISTS tenant_isolation_versions ON config_versions;
            DROP POLICY IF EXISTS tenant_isolation_values ON config_values;
            DROP POLICY IF EXISTS tenant_isolation_objects ON config_objects;
            DROP POLICY IF EXISTS tenant_isolation_assets ON config_assets;

            CREATE POLICY tenant_isolation_assets ON config_assets
                USING (tenant_id = current_setting('app.current_tenant', true)::uuid);
            
            CREATE POLICY tenant_isolation_objects ON config_objects
                USING (asset_id IN (SELECT id FROM config_assets));

            CREATE POLICY tenant_isolation_values ON config_values
                USING (config_object_id IN (SELECT id FROM config_objects));

            CREATE POLICY tenant_isolation_versions ON config_versions
                USING (config_object_id IN (SELECT id FROM config_objects));
            """
        ),
    ]
