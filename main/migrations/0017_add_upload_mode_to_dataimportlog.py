# Generated manually to add upload_mode column to DataImportLog

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0016_add_data_type_to_dataimportlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataimportlog',
            name='upload_mode',
            field=models.CharField(max_length=20, default='append'),
        ),
    ] 