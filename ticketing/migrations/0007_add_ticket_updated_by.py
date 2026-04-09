from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ticketing', '0006_scheduledasset_scheduledexecutionreport_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='updated_by',
            field=models.ForeignKey(
                blank=True,
                help_text='User who last updated the ticket',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='updated_tickets',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]

