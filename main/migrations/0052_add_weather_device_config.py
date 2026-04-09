# Generated migration for adding weather_device_config to device_list

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0051_make_cells_per_module_optional'),
    ]

    operations = [
        migrations.RunSQL(
            # Add weather_device_config column if it doesn't exist
            sql="""
                DO $$
                BEGIN
                    IF to_regclass('public.device_list') IS NULL THEN
                        RETURN;
                    END IF;

                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'device_list' 
                        AND column_name = 'weather_device_config'
                    ) THEN
                        ALTER TABLE device_list 
                        ADD COLUMN weather_device_config JSONB NULL;
                        
                        COMMENT ON COLUMN device_list.weather_device_config IS 
                        'Weather device configuration with fallback support. Format: {"irradiance_devices": ["device1", "device2"], "temperature_devices": ["device1", "device2"], "wind_devices": ["device1", "device2"]}';
                    END IF;
                END $$;
            """,
            # Reverse migration: drop the column
            reverse_sql="""
                DO $$
                BEGIN
                    IF to_regclass('public.device_list') IS NULL THEN
                        RETURN;
                    END IF;

                    ALTER TABLE device_list 
                    DROP COLUMN IF EXISTS weather_device_config;
                END $$;
            """
        ),
    ]
