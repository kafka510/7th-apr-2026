# Generated migration for Power Model Parameters History table (generic)

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0054_add_timeseries_unique_constraint'),
    ]

    operations = [
        migrations.CreateModel(
            name='PowerModelParametersHistory',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('model_code', models.CharField(db_index=True, help_text='Power model code (e.g., sdm_array_v1, ml_lstm_v1)', max_length=50)),
                ('model_version', models.CharField(blank=True, help_text='Model version', max_length=20, null=True)),
                ('parameter_type', models.CharField(
                    choices=[
                        ('datasheet', 'Datasheet-based (panel parameters)'),
                        ('device', 'Device-based (ML-learned, device-specific)'),
                        ('hybrid', 'Hybrid (combination of datasheet and device)'),
                    ],
                    db_index=True,
                    default='datasheet',
                    help_text='Type of parameters: datasheet-based or device-specific',
                    max_length=20
                )),
                ('module_datasheet_id', models.IntegerField(
                    blank=True,
                    db_index=True,
                    help_text='PVModuleDatasheet ID (for datasheet-based parameters)',
                    null=True
                )),
                ('device_id', models.CharField(
                    blank=True,
                    db_index=True,
                    help_text='Device ID (for device-specific ML parameters)',
                    max_length=120,
                    null=True
                )),
                ('asset_code', models.CharField(
                    blank=True,
                    db_index=True,
                    help_text='Asset/Site code (for reference)',
                    max_length=255,
                    null=True
                )),
                ('parameters', models.JSONField(help_text='Model parameters in JSON format. Structure varies by model.')),
                ('calculated_at', models.DateTimeField(db_index=True, help_text='When parameters were calculated (UTC)')),
                ('timezone', models.CharField(
                    help_text="Site timezone offset in format '+05:30' or '-08:00'",
                    max_length=10,
                    validators=[
                        django.core.validators.RegexValidator(
                            code='invalid_timezone',
                            message='Timezone must be in format "+05:30" or "-08:00"',
                            regex='^[+-](0[0-9]|1[0-2]):[0-5][0-9]$'
                        )
                    ]
                )),
                ('fit_quality', models.FloatField(blank=True, help_text='Quality metric of the fit (lower is better)', null=True)),
                ('fit_method', models.CharField(blank=True, help_text='Method used to fit parameters (e.g., least_squares, ml_training, manual)', max_length=50, null=True)),
                ('training_data_count', models.IntegerField(blank=True, help_text='Number of data points used for fitting/training', null=True)),
                ('context_data', models.JSONField(
                    blank=True,
                    help_text='Context data when parameters were calculated (e.g., weather conditions, array config, irradiance_avg, temperature_avg)',
                    null=True
                )),
                ('metadata', models.JSONField(
                    blank=True,
                    help_text='Additional metadata (e.g., calculation settings, model config, notes)',
                    null=True
                )),
                ('is_active', models.BooleanField(db_index=True, default=True, help_text='Whether these parameters are currently active/used')),
                ('is_validated', models.BooleanField(default=False, help_text='Whether parameters have been validated')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'power_model_parameters_history',
                'ordering': ['-calculated_at'],
            },
        ),
        migrations.AddIndex(
            model_name='powermodelparametershistory',
            index=models.Index(fields=['model_code', 'parameter_type', '-calculated_at'], name='main_power_m_model_c_1a2b3c_idx'),
        ),
        migrations.AddIndex(
            model_name='powermodelparametershistory',
            index=models.Index(fields=['module_datasheet_id', '-calculated_at'], name='main_power_m_module__idx'),
        ),
        migrations.AddIndex(
            model_name='powermodelparametershistory',
            index=models.Index(fields=['device_id', '-calculated_at'], name='main_power_m_device__idx'),
        ),
        migrations.AddIndex(
            model_name='powermodelparametershistory',
            index=models.Index(fields=['asset_code', '-calculated_at'], name='main_power_m_asset_c_idx'),
        ),
        migrations.AddIndex(
            model_name='powermodelparametershistory',
            index=models.Index(fields=['device_id', 'model_code', '-calculated_at'], name='main_power_m_device_m_idx'),
        ),
        migrations.AddIndex(
            model_name='powermodelparametershistory',
            index=models.Index(fields=['module_datasheet_id', 'model_code', '-calculated_at'], name='main_power_m_module_m_idx'),
        ),
        migrations.AddIndex(
            model_name='powermodelparametershistory',
            index=models.Index(fields=['calculated_at'], name='main_power_m_calculat_idx'),
        ),
        migrations.AddIndex(
            model_name='powermodelparametershistory',
            index=models.Index(fields=['is_active', '-calculated_at'], name='main_power_m_is_acti_idx'),
        ),
    ]

