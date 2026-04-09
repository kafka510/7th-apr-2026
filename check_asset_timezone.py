#!/usr/bin/env python
"""
Check asset timezone from AssetList table
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_app.settings')
django.setup()

from main.models import AssetList
import pytz

def check_asset_timezone():
    print("=== Checking Asset Timezone ===")
    
    # Check the specific asset
    asset_code = "NE=50590102"
    try:
        asset = AssetList.objects.get(asset_code=asset_code)
        print(f"Asset: {asset.asset_name}")
        print(f"Asset Code: {asset.asset_code}")
        print(f"Timezone from DB: '{asset.timezone}'")
        
        # Parse timezone like the code does
        tz_offset = asset.timezone
        hours, minutes = map(int, tz_offset.replace('+', '').replace('-', '').split(':'))
        total_offset = hours * 60 + minutes
        if tz_offset.startswith('-'):
            total_offset = -total_offset
        
        site_timezone = pytz.FixedOffset(total_offset)
        print(f"Parsed timezone: {site_timezone}")
        print(f"Timezone offset: {total_offset} minutes")
        
        # Test a sample conversion
        from datetime import datetime
        test_utc = pytz.UTC.localize(datetime(2025, 10, 2, 12, 0, 0))
        test_local = test_utc.astimezone(site_timezone)
        print(f"Sample conversion: {test_utc} UTC -> {test_local} {site_timezone}")
        
    except AssetList.DoesNotExist:
        print(f"Asset {asset_code} not found")
    except Exception as e:
        print(f"Error: {e}")
    
    # Check all assets to see timezone patterns
    print(f"\n=== All Asset Timezones ===")
    assets = AssetList.objects.all()[:10]
    for asset in assets:
        print(f"{asset.asset_code}: {asset.asset_name} -> '{asset.timezone}'")

if __name__ == "__main__":
    check_asset_timezone()
