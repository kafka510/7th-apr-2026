# UserActivityLog: peer_ip, forwarded_for, client_ip for audit trail.

from django.db import migrations, models
from django.db.models import F


def backfill_client_ip(apps, schema_editor):
    UserActivityLog = apps.get_model("main", "UserActivityLog")
    UserActivityLog.objects.filter(client_ip__isnull=True).update(client_ip=F("ip_address"))


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0066_asset_list_provider_asset_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="useractivitylog",
            name="peer_ip",
            field=models.CharField(
                blank=True,
                default="",
                help_text="REMOTE_ADDR as seen by Django (e.g. proxy loopback vs direct)",
                max_length=45,
            ),
        ),
        migrations.AddField(
            model_name="useractivitylog",
            name="forwarded_for",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Raw HTTP X-Forwarded-For header",
            ),
        ),
        migrations.AddField(
            model_name="useractivitylog",
            name="client_ip",
            field=models.GenericIPAddressField(
                blank=True,
                help_text="Resolved client IP: first X-Forwarded-For hop when present, else peer",
                null=True,
            ),
        ),
        migrations.RunPython(backfill_client_ip, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="useractivitylog",
            name="client_ip",
            field=models.GenericIPAddressField(
                help_text="Resolved client IP: first X-Forwarded-For hop when present, else peer",
            ),
        ),
    ]
