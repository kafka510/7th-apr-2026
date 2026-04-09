# Generated manually to add file_size column to DataImportLog

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0018_add_records_skipped_to_dataimportlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataimportlog',
            name='file_size',
            field=models.IntegerField(default=0, help_text='File size in bytes'),
        ),
    ] 