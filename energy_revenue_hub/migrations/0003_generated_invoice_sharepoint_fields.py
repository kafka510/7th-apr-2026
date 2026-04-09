from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("energy_revenue_hub", "0002_level3_invoice_intelligence"),
    ]

    operations = [
        migrations.AddField(
            model_name="generatedinvoice",
            name="sharepoint_item_id",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="generatedinvoice",
            name="sharepoint_remote_path",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="generatedinvoice",
            name="sharepoint_upload_error",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="generatedinvoice",
            name="sharepoint_upload_status",
            field=models.CharField(blank=True, default="pending_local", max_length=32),
        ),
        migrations.AddField(
            model_name="generatedinvoice",
            name="sharepoint_web_url",
            field=models.TextField(blank=True, default=""),
        ),
    ]

