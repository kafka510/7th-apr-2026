import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def migrate_subcategories(apps, schema_editor):
    Ticket = apps.get_model('ticketing', 'Ticket')
    TicketSubCategory = apps.get_model('ticketing', 'TicketSubCategory')
    db_alias = schema_editor.connection.alias

    for ticket in Ticket.objects.using(db_alias).all():
        metadata = ticket.metadata or {}
        sub_name = metadata.get('sub_category')
        if not sub_name:
            continue
        if not ticket.category_id:
            continue

        subcategory, _ = TicketSubCategory.objects.using(db_alias).get_or_create(
            category_id=ticket.category_id,
            name=sub_name,
            defaults={
                'description': '',
                'display_order': 0,
                'is_active': True,
            },
        )
        ticket.sub_category_id = subcategory.id
        ticket.save(update_fields=['sub_category'])


def noop_reverse(apps, schema_editor):
    """We intentionally keep the new FK even if reversing the migration."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('ticketing', '0007_add_ticket_updated_by'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TicketSubCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Sub-category name', max_length=100)),
                ('description', models.TextField(blank=True, help_text='Sub-category description')),
                ('display_order', models.IntegerField(default=0, help_text='Display order in UI')),
                ('is_active', models.BooleanField(default=True, help_text='Active status')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(help_text='Parent category', on_delete=django.db.models.deletion.PROTECT, related_name='subcategories', to='ticketing.ticketcategory')),
            ],
            options={
                'verbose_name': 'Ticket Sub-Category',
                'verbose_name_plural': 'Ticket Sub-Categories',
                'db_table': 'teckting_ticketsubcategory',
                'ordering': ['display_order', 'name'],
                'unique_together': {('category', 'name')},
            },
        ),
        migrations.CreateModel(
            name='TicketMaterial',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('material_name', models.CharField(help_text='Name/description of the material', max_length=200)),
                ('quantity', models.DecimalField(decimal_places=2, help_text='Quantity used', max_digits=10)),
                ('unit_price', models.DecimalField(decimal_places=2, help_text='Price per unit', max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ticket', models.ForeignKey(help_text='Associated ticket', on_delete=django.db.models.deletion.CASCADE, related_name='materials', to='ticketing.ticket')),
            ],
            options={
                'verbose_name': 'Ticket Material',
                'verbose_name_plural': 'Ticket Materials',
                'db_table': 'teckting_ticketmaterial',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='TicketManpower',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('person_name', models.CharField(help_text='Technician or personnel name', max_length=200)),
                ('hours_worked', models.DecimalField(decimal_places=2, help_text='Hours worked', max_digits=10)),
                ('hourly_rate', models.DecimalField(decimal_places=2, help_text='Hourly rate', max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ticket', models.ForeignKey(help_text='Associated ticket', on_delete=django.db.models.deletion.CASCADE, related_name='manpower_entries', to='ticketing.ticket')),
            ],
            options={
                'verbose_name': 'Ticket Manpower Entry',
                'verbose_name_plural': 'Ticket Manpower Entries',
                'db_table': 'teckting_ticketmanpower',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddField(
            model_name='ticket',
            name='sub_category',
            field=models.ForeignKey(blank=True, help_text='Sub-category within the selected category', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tickets', to='ticketing.ticketsubcategory'),
        ),
        migrations.RunPython(migrate_subcategories, reverse_code=noop_reverse),
    ]

