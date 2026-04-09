# Level 3 – Invoice Intelligence models

import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('energy_revenue_hub', '0001_add_billing_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='VendorTemplate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('vendor_key', models.CharField(max_length=100, unique=True)),
                ('config', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'vendor_templates',
            },
        ),
        migrations.CreateModel(
            name='InvoiceEmbedding',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('vendor', models.CharField(max_length=100)),
                ('embedding_json', models.JSONField(default=list)),
                ('text_preview', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'invoice_embeddings',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='InvoiceFieldCorrection',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('field_name', models.CharField(max_length=100)),
                ('original_value', models.TextField(blank=True)),
                ('corrected_value', models.TextField(blank=True)),
                ('vendor', models.CharField(max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('invoice', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='field_corrections', to='energy_revenue_hub.parsedinvoice')),
            ],
            options={
                'db_table': 'invoice_field_corrections',
                'ordering': ['-created_at'],
            },
        ),
    ]
