# Generated manually to add records_skipped column to DataImportLog

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0017_add_upload_mode_to_dataimportlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataimportlog',
            name='records_skipped',
            field=models.IntegerField(default=0),
        ),
    ] 