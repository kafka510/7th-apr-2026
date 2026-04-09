# Generated manually for device_list PV module columns
# Since device_list is an unmanaged model, we use raw SQL to add columns

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0049_create_pv_module_and_power_model_tables'),
    ]

    operations = [
        migrations.RunSQL(
            # Forward migration - Add PV module columns to device_list
            sql="""
                -- Check and add module_datasheet_id with foreign key
                DO $$ 
                BEGIN
                    IF to_regclass('public.device_list') IS NULL THEN
                        RETURN;
                    END IF;

                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'device_list' AND column_name = 'module_datasheet_id'
                    ) THEN
                        ALTER TABLE device_list 
                        ADD COLUMN module_datasheet_id INTEGER NULL;
                        
                        ALTER TABLE device_list
                        ADD CONSTRAINT fk_device_list_module_datasheet
                        FOREIGN KEY (module_datasheet_id) 
                        REFERENCES pv_module_datasheet(id) 
                        ON DELETE SET NULL;
                        
                        CREATE INDEX idx_device_list_module_datasheet 
                        ON device_list(module_datasheet_id);
                    END IF;
                END $$;
                
                -- Add string configuration columns
                DO $$ 
                BEGIN
                    IF to_regclass('public.device_list') IS NULL THEN
                        RETURN;
                    END IF;

                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'device_list' AND column_name = 'modules_in_series') THEN
                        ALTER TABLE device_list ADD COLUMN modules_in_series INTEGER NULL;
                    END IF;
                    
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'device_list' AND column_name = 'installation_date') THEN
                        ALTER TABLE device_list ADD COLUMN installation_date DATE NULL;
                    END IF;
                    
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'device_list' AND column_name = 'tilt_angle') THEN
                        ALTER TABLE device_list ADD COLUMN tilt_angle FLOAT NULL;
                    END IF;
                    
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'device_list' AND column_name = 'azimuth_angle') THEN
                        ALTER TABLE device_list ADD COLUMN azimuth_angle FLOAT NULL;
                    END IF;
                    
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'device_list' AND column_name = 'mounting_type') THEN
                        ALTER TABLE device_list ADD COLUMN mounting_type VARCHAR(50) NULL;
                    END IF;
                END $$;
                
                -- Add loss factor columns
                DO $$ 
                BEGIN
                    IF to_regclass('public.device_list') IS NULL THEN
                        RETURN;
                    END IF;

                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'device_list' AND column_name = 'expected_soiling_loss') THEN
                        ALTER TABLE device_list ADD COLUMN expected_soiling_loss FLOAT DEFAULT 2.0;
                    END IF;
                    
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'device_list' AND column_name = 'shading_factor') THEN
                        ALTER TABLE device_list ADD COLUMN shading_factor FLOAT DEFAULT 0.0;
                    END IF;
                END $$;
                
                -- Add measured performance columns
                DO $$ 
                BEGIN
                    IF to_regclass('public.device_list') IS NULL THEN
                        RETURN;
                    END IF;

                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'device_list' AND column_name = 'measured_degradation_rate') THEN
                        ALTER TABLE device_list ADD COLUMN measured_degradation_rate FLOAT NULL;
                    END IF;
                    
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'device_list' AND column_name = 'last_performance_test_date') THEN
                        ALTER TABLE device_list ADD COLUMN last_performance_test_date DATE NULL;
                    END IF;
                    
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'device_list' AND column_name = 'operational_notes') THEN
                        ALTER TABLE device_list ADD COLUMN operational_notes TEXT NULL;
                    END IF;
                END $$;
                
                -- Add power model selection columns (Plugin Architecture)
                DO $$ 
                BEGIN
                    IF to_regclass('public.device_list') IS NULL THEN
                        RETURN;
                    END IF;

                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'device_list' AND column_name = 'power_model_id'
                    ) THEN
                        ALTER TABLE device_list 
                        ADD COLUMN power_model_id INTEGER NULL;
                        
                        ALTER TABLE device_list
                        ADD CONSTRAINT fk_device_list_power_model
                        FOREIGN KEY (power_model_id) 
                        REFERENCES power_model_registry(id) 
                        ON DELETE SET NULL;
                        
                        CREATE INDEX idx_device_list_power_model 
                        ON device_list(power_model_id);
                    END IF;
                    
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'device_list' AND column_name = 'power_model_config') THEN
                        ALTER TABLE device_list ADD COLUMN power_model_config JSONB NULL;
                    END IF;
                    
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'device_list' AND column_name = 'model_fallback_enabled') THEN
                        ALTER TABLE device_list ADD COLUMN model_fallback_enabled BOOLEAN DEFAULT TRUE;
                    END IF;
                END $$;
            """,
            
            # Reverse migration - Remove PV module columns from device_list
            reverse_sql="""
                DO $$
                BEGIN
                    IF to_regclass('public.device_list') IS NULL THEN
                        RETURN;
                    END IF;

                    -- Drop foreign key constraints first
                    ALTER TABLE device_list DROP CONSTRAINT IF EXISTS fk_device_list_module_datasheet;
                    ALTER TABLE device_list DROP CONSTRAINT IF EXISTS fk_device_list_power_model;
                    
                    -- Drop indexes
                    DROP INDEX IF EXISTS idx_device_list_module_datasheet;
                    DROP INDEX IF EXISTS idx_device_list_power_model;
                    
                    -- Drop columns
                    ALTER TABLE device_list DROP COLUMN IF EXISTS module_datasheet_id;
                    ALTER TABLE device_list DROP COLUMN IF EXISTS modules_in_series;
                    ALTER TABLE device_list DROP COLUMN IF EXISTS installation_date;
                    ALTER TABLE device_list DROP COLUMN IF EXISTS tilt_angle;
                    ALTER TABLE device_list DROP COLUMN IF EXISTS azimuth_angle;
                    ALTER TABLE device_list DROP COLUMN IF EXISTS mounting_type;
                    ALTER TABLE device_list DROP COLUMN IF EXISTS expected_soiling_loss;
                    ALTER TABLE device_list DROP COLUMN IF EXISTS shading_factor;
                    ALTER TABLE device_list DROP COLUMN IF EXISTS measured_degradation_rate;
                    ALTER TABLE device_list DROP COLUMN IF EXISTS last_performance_test_date;
                    ALTER TABLE device_list DROP COLUMN IF EXISTS operational_notes;
                    ALTER TABLE device_list DROP COLUMN IF EXISTS power_model_id;
                    ALTER TABLE device_list DROP COLUMN IF EXISTS power_model_config;
                    ALTER TABLE device_list DROP COLUMN IF EXISTS model_fallback_enabled;
                END $$;
            """
        ),
    ]

