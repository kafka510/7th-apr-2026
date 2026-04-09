# Generated migration to make device_mapping.id column auto-generating

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0052_add_weather_device_config'),
    ]

    operations = [
        migrations.RunSQL(
            # Make id column auto-generating using a sequence
            sql="""
                DO $$
                DECLARE
                    seq_name TEXT := 'device_mapping_id_seq';
                    max_id BIGINT;
                    current_seq_val BIGINT;
                BEGIN
                    IF to_regclass('public.device_mapping') IS NULL THEN
                        RETURN;
                    END IF;

                    -- Get the maximum id value from the table
                    SELECT COALESCE(MAX(id), 0) INTO max_id FROM device_mapping;
                    
                    -- Check if sequence already exists
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_sequences 
                        WHERE schemaname = 'public' 
                        AND sequencename = seq_name
                    ) THEN
                        -- Create the sequence starting from max_id + 1
                        EXECUTE format('CREATE SEQUENCE %I START WITH %s', seq_name, max_id + 1);
                    ELSE
                        -- Sequence exists, but we need to ensure it's at least max_id + 1
                        -- Get current sequence value
                        SELECT last_value INTO current_seq_val FROM device_mapping_id_seq;
                        
                        -- If current sequence value is less than max_id, set it to max_id + 1
                        IF current_seq_val <= max_id THEN
                            EXECUTE format('SELECT setval(%L, %s, false)', seq_name, max_id + 1);
                        END IF;
                    END IF;
                    
                    -- Set the default value of the id column to use the sequence
                    EXECUTE format('ALTER TABLE device_mapping ALTER COLUMN id SET DEFAULT nextval(%L)', seq_name);
                    
                    -- Make sure the sequence is owned by the column
                    ALTER SEQUENCE device_mapping_id_seq OWNED BY device_mapping.id;
                END $$;
            """,
            # Reverse migration: remove the default and drop the sequence
            reverse_sql="""
                DO $$
                BEGIN
                    IF to_regclass('public.device_mapping') IS NULL THEN
                        RETURN;
                    END IF;

                    -- Remove the default value from the id column
                    ALTER TABLE device_mapping 
                    ALTER COLUMN id DROP DEFAULT;
                    
                    -- Drop the sequence if it exists
                    DROP SEQUENCE IF EXISTS device_mapping_id_seq;
                END $$;
            """
        ),
    ]
