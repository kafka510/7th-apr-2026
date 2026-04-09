# requires_utility_invoice for utility-led ERH billing (see BILLING_INVOICE_GENERATION_MULTI_CONTRACT_PLAN.md §10)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0073_rename_contractor_type_to_contract_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="assets_contracts",
            name="requires_utility_invoice",
            field=models.BooleanField(
                default=False,
                help_text="If true, billing requires a parsed utility invoice for the billing period (sg_ppa / utility-led flows).",
            ),
        ),
    ]
