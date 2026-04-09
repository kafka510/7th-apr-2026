# Generated manually to fix missing data_type column

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0015_auto_20250805_1647'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataimportlog',
            name='data_type',
            field=models.CharField(max_length=50, default='unknown'),
            preserve_default=False,
        ),
    ] 