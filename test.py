import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_app.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT conname, contype 
        FROM pg_constraint 
        WHERE conname = 'timeseries_data_device_ts_metric_unique'
    """)
    result = cursor.fetchone()
    
    if result:
        print(f"✓ Constraint found: {result[0]} (type: {result[1]})")
        print("The unique constraint is active and ON CONFLICT DO UPDATE will work efficiently.")
    else:
        print("✗ Constraint NOT found")
        print("This is okay - the application will use DELETE+INSERT fallback instead.")
        print("You can add the constraint later after cleaning duplicates if desired.")

