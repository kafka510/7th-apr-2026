from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("data_collection", "0007_adapter_account_and_asset_config_fk"),
    ]

    operations = [
        migrations.AlterField(
            model_name="assetadapterconfig",
            name="asset_code",
            field=models.CharField(
                db_index=True,
                help_text="Asset code (matches asset_list.asset_code)",
                max_length=255,
            ),
        ),
        migrations.AddConstraint(
            model_name="assetadapterconfig",
            constraint=models.UniqueConstraint(
                fields=("asset_code", "adapter_id"),
                name="uq_asset_adapter_config_asset_code_adapter_id",
            ),
        ),
    ]

