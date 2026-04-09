# Generated manually to add processing_time column to DataImportLog

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0019_add_file_size_to_dataimportlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataimportlog',
            name='processing_time',
            field=models.FloatField(default=0.0, help_text='Processing time in seconds'),
        ),
    ] 