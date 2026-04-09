#!/usr/bin/env python
"""
Script to add test device mapping records for NE=50590102
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_app.settings')
django.setup()

from main.models import device_mapping

def add_test_device_mappings():
    print("Adding test device mapping records for NE=50590102...")
    
    # Test asset code
    test_asset = "NE=50590102"
    
    # Sample device mappings based on common solar plant metrics
    sample_mappings = [
        # String Inverter mappings
        {
            'asset_code': test_asset,
            'device_type': 'string_inv',
            'oem_tag': 'power_output',
            'discription': 'Power Output',
            'data_type': 'float',
            'units': 'kW',
            'metric': 'power_output'
        },
        {
            'asset_code': test_asset,
            'device_type': 'string_inv',
            'oem_tag': 'voltage_dc',
            'discription': 'DC Voltage',
            'data_type': 'float',
            'units': 'V',
            'metric': 'voltage_dc'
        },
        {
            'asset_code': test_asset,
            'device_type': 'string_inv',
            'oem_tag': 'current_dc',
            'discription': 'DC Current',
            'data_type': 'float',
            'units': 'A',
            'metric': 'current_dc'
        },
        {
            'asset_code': test_asset,
            'device_type': 'string_inv',
            'oem_tag': 'frequency',
            'discription': 'AC Frequency',
            'data_type': 'float',
            'units': 'Hz',
            'metric': 'frequency'
        },
        {
            'asset_code': test_asset,
            'device_type': 'string_inv',
            'oem_tag': 'temperature',
            'discription': 'Inverter Temperature',
            'data_type': 'float',
            'units': '°C',
            'metric': 'temperature'
        },
        
        # Weather Station mappings
        {
            'asset_code': test_asset,
            'device_type': 'wst',
            'oem_tag': 'irradiance',
            'discription': 'Solar Irradiance',
            'data_type': 'float',
            'units': 'W/m²',
            'metric': 'irradiance'
        },
        {
            'asset_code': test_asset,
            'device_type': 'wst',
            'oem_tag': 'module_temp',
            'discription': 'Module Temperature',
            'data_type': 'float',
            'units': '°C',
            'metric': 'module_temp'
        },
        {
            'asset_code': test_asset,
            'device_type': 'wst',
            'oem_tag': 'ambient_temp',
            'discription': 'Ambient Temperature',
            'data_type': 'float',
            'units': '°C',
            'metric': 'ambient_temp'
        },
        {
            'asset_code': test_asset,
            'device_type': 'wst',
            'oem_tag': 'wind_speed',
            'discription': 'Wind Speed',
            'data_type': 'float',
            'units': 'm/s',
            'metric': 'wind_speed'
        },
        {
            'asset_code': test_asset,
            'device_type': 'wst',
            'oem_tag': 'humidity',
            'discription': 'Humidity',
            'data_type': 'float',
            'units': '%',
            'metric': 'humidity'
        },
        
        # Grid Meter mappings
        {
            'asset_code': test_asset,
            'device_type': 'gmt',
            'oem_tag': 'active_power',
            'discription': 'Active Power',
            'data_type': 'float',
            'units': 'kW',
            'metric': 'active_power'
        },
        {
            'asset_code': test_asset,
            'device_type': 'gmt',
            'oem_tag': 'reactive_power',
            'discription': 'Reactive Power',
            'data_type': 'float',
            'units': 'kVAR',
            'metric': 'reactive_power'
        },
        {
            'asset_code': test_asset,
            'device_type': 'gmt',
            'oem_tag': 'voltage_l1',
            'discription': 'Line 1 Voltage',
            'data_type': 'float',
            'units': 'V',
            'metric': 'voltage_l1'
        },
        {
            'asset_code': test_asset,
            'device_type': 'gmt',
            'oem_tag': 'current_l1',
            'discription': 'Line 1 Current',
            'data_type': 'float',
            'units': 'A',
            'metric': 'current_l1'
        }
    ]
    
    # Add the mappings
    created_count = 0
    for mapping_data in sample_mappings:
        try:
            # Check if mapping already exists
            existing = device_mapping.objects.filter(
                asset_code=mapping_data['asset_code'],
                device_type=mapping_data['device_type'],
                metric=mapping_data['metric']
            ).first()
            
            if not existing:
                # Get the next available ID
                max_id = device_mapping.objects.aggregate(max_id=models.Max('id'))['max_id']
                mapping_data['id'] = (max_id or 0) + created_count + 1
                
                device_mapping.objects.create(**mapping_data)
                created_count += 1
                print(f"  ✓ Created: {mapping_data['device_type']} - {mapping_data['metric']}")
            else:
                print(f"  - Exists: {mapping_data['device_type']} - {mapping_data['metric']}")
                
        except Exception as e:
            print(f"  ✗ Error creating {mapping_data['device_type']} - {mapping_data['metric']}: {e}")
    
    print(f"\nCreated {created_count} new device mapping records for {test_asset}")
    
    # Verify the mappings were created
    total_mappings = device_mapping.objects.filter(asset_code=test_asset).count()
    print(f"Total device mappings for {test_asset}: {total_mappings}")
    
    if total_mappings > 0:
        print("\nDevice types with mappings:")
        device_types = device_mapping.objects.filter(asset_code=test_asset).values_list('device_type', flat=True).distinct()
        for dt in device_types:
            count = device_mapping.objects.filter(asset_code=test_asset, device_type=dt).count()
            print(f"  - {dt}: {count} metrics")

if __name__ == "__main__":
    from django.db import models
    add_test_device_mappings()
