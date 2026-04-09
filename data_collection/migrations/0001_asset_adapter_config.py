# Generated manually for data_collection app

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='AssetAdapterConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('asset_code', models.CharField(db_index=True, help_text='Asset code (matches asset_list.asset_code)', max_length=255, unique=True)),
                ('adapter_id', models.CharField(help_text="Adapter registry key (e.g. 'stub', 'sungrow', 'solargis')", max_length=64)),
                ('config', models.JSONField(blank=True, default=dict, help_text='Adapter-specific options (API URL, credentials, device filters, etc.)')),
                ('acquisition_interval_minutes', models.PositiveSmallIntegerField(choices=[(5, '5 minutes'), (30, '30 minutes')], default=5, help_text='Run this asset on 5-min or 30-min acquisition schedule')),
                ('enabled', models.BooleanField(default=True, help_text='If False, skip this asset during acquisition runs')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Asset adapter config',
                'verbose_name_plural': 'Asset adapter configs',
                'db_table': 'data_collection_asset_adapter_config',
                'ordering': ['asset_code'],
            },
        ),
    ]
