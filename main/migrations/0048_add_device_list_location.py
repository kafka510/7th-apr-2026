# Generated manually for device_list location column
# Since device_list is an unmanaged model, we use raw SQL to add column

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0047_bessv1data'),
    ]

    operations = [
        # Add location column to device_list table
        migrations.RunSQL(
            # Forward migration - add location column
            # Note: This uses PostgreSQL syntax. For other databases, adjust accordingly.
            sql="""
                DO $$ 
                BEGIN
                    IF to_regclass('public.device_list') IS NULL THEN
                        RETURN;
                    END IF;

                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'device_list' AND column_name = 'location'
                    ) THEN
                        ALTER TABLE device_list ADD COLUMN location VARCHAR(255);
                    END IF;
                END $$;
            """,
            # Reverse migration - remove location column (for rollback)
            reverse_sql="""
                DO $$ 
                BEGIN
                    IF to_regclass('public.device_list') IS NULL THEN
                        RETURN;
                    END IF;

                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'device_list' AND column_name = 'location'
                    ) THEN
                        ALTER TABLE device_list DROP COLUMN location;
                    END IF;
                END $$;
            """
        ),
    ]

