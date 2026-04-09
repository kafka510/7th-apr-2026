#!/usr/bin/env python
"""
Debug script to check device mapping data
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_app.settings')
django.setup()

from main.models import device_mapping, device_list

def debug_device_mapping():
    print("=== Device Mapping Debug ===")
    
    # Check what asset codes exist in device_mapping
    asset_codes = device_mapping.objects.values_list('asset_code', flat=True).distinct()
    print(f"Asset codes in device_mapping: {list(asset_codes)[:10]}...")
    
    # Check for the specific asset you're testing
    test_asset = "NE=50590102"  # Based on your screenshot
    print(f"\n=== Checking asset: {test_asset} ===")
    
    # Check device_mapping for this asset
    mapping_records = device_mapping.objects.filter(asset_code=test_asset)
    print(f"Device mapping records for {test_asset}: {mapping_records.count()}")
    
    if mapping_records.exists():
        print("\nDevice types in device_mapping:")
        device_types = mapping_records.values_list('device_type', flat=True).distinct()
        for dt in device_types:
            print(f"  - {dt}")
            
        print("\nSample measurement points:")
        for mp in mapping_records[:5]:
            print(f"  {mp.device_type} - {mp.metric} - {mp.discription}")
    
    # Check device_list for this asset
    print(f"\n=== Checking device_list for {test_asset} ===")
    devices = device_list.objects.filter(parent_code=test_asset)
    print(f"Devices in device_list: {devices.count()}")
    
    if devices.exists():
        print("\nDevice types in device_list:")
        device_types = devices.values_list('device_type', flat=True).distinct()
        for dt in device_types:
            print(f"  - {dt}")
            
        print("\nSample devices:")
        for device in devices[:5]:
            print(f"  {device.device_name} - {device.device_type} - {device.device_id}")
    
    # Check if there's a mismatch
    print(f"\n=== Checking for mismatches ===")
    mapping_types = set(mapping_records.values_list('device_type', flat=True).distinct())
    device_types = set(devices.values_list('device_type', flat=True).distinct())
    
    print(f"Device types in device_mapping: {mapping_types}")
    print(f"Device types in device_list: {device_types}")
    print(f"Mismatch (in mapping but not in devices): {mapping_types - device_types}")
    print(f"Mismatch (in devices but not in mapping): {device_types - mapping_types}")

if __name__ == "__main__":
    debug_device_mapping()
