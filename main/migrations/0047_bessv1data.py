from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0046_alter_userprofile_role'),
    ]

    operations = [
        migrations.CreateModel(
            name='BESSV1Data',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('month', models.CharField(max_length=20)),
                ('country', models.CharField(max_length=100)),
                ('portfolio', models.CharField(max_length=100)),
                ('asset_no', models.CharField(max_length=100)),
                ('battery_capacity_mwh', models.FloatField(blank=True, null=True)),
                ('actual_pv_energy_kwh', models.FloatField(blank=True, null=True)),
                ('actual_export_energy_kwh', models.FloatField(blank=True, null=True)),
                ('actual_charge_energy_kwh', models.FloatField(blank=True, null=True)),
                ('actual_discharge_energy', models.FloatField(blank=True, null=True)),
                ('actual_pv_grid_kwh', models.FloatField(blank=True, null=True)),
                ('actual_system_losses', models.FloatField(blank=True, null=True)),
                ('min_soc', models.FloatField(blank=True, null=True)),
                ('max_soc', models.FloatField(blank=True, null=True)),
                ('min_ess_temp', models.FloatField(blank=True, null=True)),
                ('max_ess_temp', models.FloatField(blank=True, null=True)),
                ('actual_avg_rte', models.FloatField(blank=True, null=True)),
                ('actual_cuf', models.FloatField(blank=True, null=True)),
                ('actual_no_of_cycles', models.IntegerField(blank=True, null=True)),
                ('budget_pv_energy_kwh', models.FloatField(blank=True, null=True)),
                ('budget_export_energy_kwh', models.FloatField(blank=True, null=True)),
                ('budget_charge_energy_kwh', models.FloatField(blank=True, null=True)),
                ('budget_discharge_energy', models.FloatField(blank=True, null=True)),
                ('budget_pv_grid_kwh', models.FloatField(blank=True, null=True)),
                ('budget_system_losses', models.FloatField(blank=True, null=True)),
                ('budget_cuf', models.FloatField(blank=True, null=True)),
                ('budget_no_of_cycles', models.IntegerField(blank=True, null=True)),
                ('budget_grid_import_kwh', models.FloatField(blank=True, null=True)),
                ('actual_grid_import_kwh', models.FloatField(blank=True, null=True)),
                ('budget_avg_rte', models.FloatField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'bess_v1_data',
            },
        ),
        migrations.AddConstraint(
            model_name='bessv1data',
            constraint=models.UniqueConstraint(fields=('month', 'asset_no'), name='unique_bess_v1_month_asset'),
        ),
        migrations.AddIndex(
            model_name='bessv1data',
            index=models.Index(fields=['month'], name='bess_v1_month_idx'),
        ),
        migrations.AddIndex(
            model_name='bessv1data',
            index=models.Index(fields=['portfolio'], name='bess_v1_portfolio_idx'),
        ),
    ]

