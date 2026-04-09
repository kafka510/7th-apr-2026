from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
    ("main", "0077_merge_20260331_1116"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name="assets_contracts",
                    name="due_days",
                    field=models.IntegerField(
                        null=True,
                        blank=True,
                        help_text="Invoice due days offset from invoice date.",
                    ),
                ),
                migrations.AddField(
                    model_name="yielddata",
                    name="budgeted_grid_curtailment",
                    field=models.FloatField(null=True, blank=True),
                ),
            ],
        ),
    ]