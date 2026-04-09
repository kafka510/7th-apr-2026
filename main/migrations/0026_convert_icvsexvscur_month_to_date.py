# Generated migration for converting month field from CharField to DateField

from django.db import migrations, models
from datetime import datetime

def convert_month_to_date(apps, schema_editor):
    """Convert month strings like '25-Apr' to date objects like '2025-04-01'"""
    ICVSEXVSCURData = apps.get_model('main', 'ICVSEXVSCURData')
    
    month_mapping = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
    for record in ICVSEXVSCURData.objects.all():
        try:
            # Parse month string like "25-Apr"
            if record.month and '-' in record.month:
                parts = record.month.split('-')
                if len(parts) == 2:
                    year_part = parts[0]
                    month_part = parts[1].lower()
                    
                    # Determine year (assuming 25 means 2025)
                    if year_part.isdigit():
                        year = 2000 + int(year_part) if int(year_part) < 100 else int(year_part)
                    else:
                        year = 2025  # Default fallback
                    
                    # Get month number
                    month_num = month_mapping.get(month_part, 1)
                    
                    # Create date object for 1st day of the month
                    record.month_date = datetime(year, month_num, 1).date()
                    record.save()
                    print(f"Converted {record.month} to {record.month_date}")
        except Exception as e:
            print(f"Error converting month '{record.month}' for record {record.id}: {e}")
            # Set a default date if conversion fails
            record.month_date = datetime(2025, 1, 1).date()
            record.save()

def reverse_convert_month_to_date(apps, schema_editor):
    """Reverse migration - convert date back to string"""
    ICVSEXVSCURData = apps.get_model('main', 'ICVSEXVSCURData')
    
    month_names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    for record in ICVSEXVSCURData.objects.all():
        if record.month_date:
            year_short = str(record.month_date.year)[-2:]  # Get last 2 digits of year
            month_name = month_names[record.month_date.month]
            record.month = f"{year_short}-{month_name}"
            record.save()

class Migration(migrations.Migration):

    dependencies = [
        ('main', '0025_add_realtime_csv_fields_to_real_time_kpi'),
    ]

    operations = [
        # Add new month_date field
        migrations.AddField(
            model_name='icvsexvscurdata',
            name='month_date',
            field=models.DateField(null=True, blank=True, help_text='Month as first day of the month'),
        ),
        
        # Run data migration to convert existing data
        migrations.RunPython(convert_month_to_date, reverse_convert_month_to_date),
        
        # Remove old month field
        migrations.RemoveField(
            model_name='icvsexvscurdata',
            name='month',
        ),
        
        # Rename month_date to month
        migrations.RenameField(
            model_name='icvsexvscurdata',
            old_name='month_date',
            new_name='month',
        ),
        
        # Make month field non-nullable
        migrations.AlterField(
            model_name='icvsexvscurdata',
            name='month',
            field=models.DateField(help_text='Month as first day of the month'),
        ),
    ]
