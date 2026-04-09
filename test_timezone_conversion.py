#!/usr/bin/env python
"""
Test script to verify timezone conversion logic
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_app.settings')
django.setup()

import pytz
from datetime import datetime
from main.models import timeseries_data

def test_timezone_conversion():
    print("=== Testing Timezone Conversion Logic ===")
    
    # Test different timezone scenarios
    test_cases = [
        {
            'name': 'UTC timestamp (no timezone)',
            'db_timestamp': datetime(2025, 10, 9, 12, 0, 0),  # No timezone
            'site_timezone_str': '+08:00'
        },
        {
            'name': 'UTC timestamp (with UTC timezone)',
            'db_timestamp': pytz.UTC.localize(datetime(2025, 10, 9, 12, 0, 0)),
            'site_timezone_str': '+08:00'
        },
        {
            'name': 'Timestamp with different timezone (+05:30)',
            'db_timestamp': pytz.FixedOffset(330).localize(datetime(2025, 10, 9, 12, 0, 0)),  # +05:30
            'site_timezone_str': '+08:00'
        }
    ]
    
    for test_case in test_cases:
        print(f"\n--- {test_case['name']} ---")
        
        ts_from_db = test_case['db_timestamp']
        site_timezone_str = test_case['site_timezone_str']
        
        # Parse site timezone
        hours, minutes = map(int, site_timezone_str.replace('+', '').replace('-', '').split(':'))
        total_offset = hours * 60 + minutes
        if site_timezone_str.startswith('-'):
            total_offset = -total_offset
        site_timezone = pytz.FixedOffset(total_offset)
        
        print(f"Original DB timestamp: {ts_from_db}")
        print(f"DB timestamp timezone: {ts_from_db.tzinfo}")
        print(f"Site timezone: {site_timezone_str} ({site_timezone})")
        
        # Apply conversion logic
        if ts_from_db.tzinfo is None:
            ts_utc = pytz.UTC.localize(ts_from_db)
            print(f"No timezone in DB timestamp, assuming UTC: {ts_from_db}")
        else:
            ts_utc = ts_from_db.astimezone(pytz.UTC)
            print(f"DB timestamp has timezone, converted to UTC: {ts_utc}")
        
        ts_local = ts_utc.astimezone(site_timezone)
        print(f"Final local time: {ts_local}")
        print(f"Conversion: {ts_from_db} -> {ts_utc} -> {ts_local}")

def check_sample_timeseries_data():
    print("\n=== Checking Sample Timeseries Data ===")
    
    # Get a sample record
    sample_record = timeseries_data.objects.first()
    if sample_record:
        print(f"Sample timeseries record:")
        print(f"  Device ID: {sample_record.device_id}")
        print(f"  Metric: {sample_record.metric}")
        print(f"  Timestamp: {sample_record.ts}")
        print(f"  Timestamp timezone: {sample_record.ts.tzinfo}")
        print(f"  Value: {sample_record.value}")
    else:
        print("No timeseries data found")

if __name__ == "__main__":
    test_timezone_conversion()
    check_sample_timeseries_data()
