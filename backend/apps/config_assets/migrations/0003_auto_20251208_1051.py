from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('config_assets', '0002_alter_configobject_asset'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            -- Enable RLS on main tables
            ALTER TABLE config_assets ENABLE ROW LEVEL SECURITY;
            ALTER TABLE config_objects ENABLE ROW LEVEL SECURITY;
            ALTER TABLE config_values ENABLE ROW LEVEL SECURITY;
            ALTER TABLE config_versions ENABLE ROW LEVEL SECURITY;

            -- Policy for ConfigAsset (Root)
            -- Users can see assets belonging to their current active tenant context
            CREATE POLICY tenant_isolation_assets ON config_assets
                USING (tenant_id = current_setting('app.current_tenant', true)::uuid);
            
            -- Policy for ConfigObject (Child of Asset)
            -- Visible if parent Asset is visible
            CREATE POLICY tenant_isolation_objects ON config_objects
                USING (
                    asset_id IN (SELECT id FROM config_assets)
                );

            -- Policy for ConfigValue (Child of Object)
            -- Visible if parent Object is visible
            CREATE POLICY tenant_isolation_values ON config_values
                USING (
                    config_object_id IN (SELECT id FROM config_objects)
                );

            -- Policy for ConfigVersion (Child of Object)
            -- Visible if parent Object is visible
            CREATE POLICY tenant_isolation_versions ON config_versions
                USING (
                    config_object_id IN (SELECT id FROM config_objects)
                );
            """,
            reverse_sql="""
            DROP POLICY IF EXISTS tenant_isolation_versions ON config_versions;
            DROP POLICY IF EXISTS tenant_isolation_values ON config_values;
            DROP POLICY IF EXISTS tenant_isolation_objects ON config_objects;
            DROP POLICY IF EXISTS tenant_isolation_assets ON config_assets;

            ALTER TABLE config_versions DISABLE ROW LEVEL SECURITY;
            ALTER TABLE config_values DISABLE ROW LEVEL SECURITY;
            ALTER TABLE config_objects DISABLE ROW LEVEL SECURITY;
            ALTER TABLE config_assets DISABLE ROW LEVEL SECURITY;
            """
        ),
    ]
