# Generated manually for design alignment: contractor_type → contract_type on assets_contracts

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0072_add_kpis_oem_daily_product_kwh"),
    ]

    operations = [
        migrations.RenameField(
            model_name="assets_contracts",
            old_name="contractor_type",
            new_name="contract_type",
        ),
    ]
