# Generated manually to fix database field length issue

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0039_alter_realtimekpi_site_state'),
    ]

    operations = [
        migrations.AlterField(
            model_name='useractivitylog',
            name='resource',
            field=models.CharField(help_text='URL path or resource accessed', max_length=500),
        ),
    ]
