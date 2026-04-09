# Initial migration for generic scheduled-job deduplication table.

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ScheduledJobRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("job_name", models.CharField(db_index=True, max_length=100)),
                ("run_date", models.DateField(blank=True, db_index=True, null=True)),
                ("scope_key", models.CharField(db_index=True, max_length=255)),
                ("triggered_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                "db_table": "scheduled_job_run",
                "ordering": ["-triggered_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="scheduledjobrun",
            constraint=models.UniqueConstraint(
                fields=("job_name", "run_date", "scope_key"),
                name="scheduled_job_run_uniq",
            ),
        ),
    ]

