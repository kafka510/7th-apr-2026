from django.core.management.base import BaseCommand
from django.db import connection
from main.models import AssetList, device_list, device_mapping
import logging

class Command(BaseCommand):
    help = 'Find and report corrupted Japanese characters in the database'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Actually fix the corrupted data (WARNING: This will clear corrupted fields)'
        )
        parser.add_argument(
            '--table',
            type=str,
            choices=['asset_list', 'device_list', 'device_mapping', 'all'],
            default='all',
            help='Which table to scan/fix'
        )
    
    def handle(self, *args, **options):
        fix_mode = options['fix']
        table_name = options['table']
        
        self.stdout.write(self.style.WARNING(
            f"🔍 Scanning for corrupted Japanese characters in {table_name}..."
        ))
        
        corrupted_count = 0
        fixed_count = 0
        
        if table_name in ['asset_list', 'all']:
            count, fixed = self.scan_asset_list(fix_mode)
            corrupted_count += count
            fixed_count += fixed
            
        if table_name in ['device_list', 'all']:
            count, fixed = self.scan_device_list(fix_mode)
            corrupted_count += count
            fixed_count += fixed
            
        if table_name in ['device_mapping', 'all']:
            count, fixed = self.scan_device_mapping(fix_mode)
            corrupted_count += count
            fixed_count += fixed
        
        if corrupted_count > 0:
            if fix_mode:
                self.stdout.write(self.style.SUCCESS(
                    f"✅ Fixed {fixed_count} corrupted records out of {corrupted_count} found."
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f"⚠️  Found {corrupted_count} corrupted records. Run with --fix to clean them."
                ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "✅ No corrupted characters found! All data looks good."
            ))
    
    def scan_asset_list(self, fix_mode):
        """Scan AssetList for corrupted data"""
        corrupted_count = 0
        fixed_count = 0
        
        self.stdout.write("Scanning asset_list...")
        
        for asset in AssetList.objects.all():
            corrupted_fields = []
            
            if '?' in str(asset.asset_name):
                corrupted_fields.append('asset_name')
            if '?' in str(asset.address):
                corrupted_fields.append('address')
            if '?' in str(asset.contact_person):
                corrupted_fields.append('contact_person')
            if '?' in str(asset.contact_method):
                corrupted_fields.append('contact_method')
            if '?' in str(asset.portfolio):
                corrupted_fields.append('portfolio')
            
            if corrupted_fields:
                corrupted_count += 1
                self.stdout.write(
                    f"  - Asset {asset.asset_code}: {', '.join(corrupted_fields)}"
                )
                
                if fix_mode:
                    try:
                        with connection.cursor() as cursor:
                            # Clear corrupted fields - you may want to set them to meaningful defaults
                            update_fields = []
                            update_values = []
                            
                            for field in corrupted_fields:
                                if field == 'asset_name':
                                    update_fields.append('asset_name = %s')
                                    update_values.append(f'Asset_{asset.asset_code}')  # Default name
                                elif field == 'address':
                                    update_fields.append('address = %s')
                                    update_values.append('')  # Clear address
                                elif field == 'contact_person':
                                    update_fields.append('contact_person = %s')
                                    update_values.append('')  # Clear contact
                                elif field == 'contact_method':
                                    update_fields.append('contact_method = %s')
                                    update_values.append('')  # Clear contact method
                                elif field == 'portfolio':
                                    update_fields.append('portfolio = %s')
                                    update_values.append('Default Portfolio')  # Default portfolio
                            
                            if update_fields:
                                update_values.append(asset.asset_code)  # For WHERE clause
                                sql = f"UPDATE asset_list SET {', '.join(update_fields)} WHERE asset_code = %s"
                                cursor.execute(sql, update_values)
                                fixed_count += 1
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error fixing asset {asset.asset_code}: {e}"))
        
        return corrupted_count, fixed_count
    
    def scan_device_list(self, fix_mode):
        """Scan device_list for corrupted data"""
        corrupted_count = 0
        fixed_count = 0
        
        self.stdout.write("Scanning device_list...")
        
        for device in device_list.objects.all():
            corrupted_fields = []
            
            if '?' in str(device.device_name):
                corrupted_fields.append('device_name')
            if '?' in str(device.device_make):
                corrupted_fields.append('device_make')
            if '?' in str(device.device_model):
                corrupted_fields.append('device_model')
            if '?' in str(device.device_type):
                corrupted_fields.append('device_type')
            if '?' in str(device.country):
                corrupted_fields.append('country')
            
            if corrupted_fields:
                corrupted_count += 1
                self.stdout.write(
                    f"  - Device {device.device_id}: {', '.join(corrupted_fields)}"
                )
                
                if fix_mode:
                    try:
                        with connection.cursor() as cursor:
                            update_fields = []
                            update_values = []
                            
                            for field in corrupted_fields:
                                if field == 'device_name':
                                    update_fields.append('device_name = %s')
                                    update_values.append(f'Device_{device.device_id}')
                                elif field == 'device_make':
                                    update_fields.append('device_make = %s')
                                    update_values.append('Unknown')
                                elif field == 'device_model':
                                    update_fields.append('device_model = %s')
                                    update_values.append('Unknown')
                                elif field == 'device_type':
                                    update_fields.append('device_type = %s')
                                    update_values.append('Unknown')
                                elif field == 'country':
                                    update_fields.append('country = %s')
                                    update_values.append('Unknown')
                            
                            if update_fields:
                                update_values.append(device.device_id)
                                sql = f"UPDATE device_list SET {', '.join(update_fields)} WHERE device_id = %s"
                                cursor.execute(sql, update_values)
                                fixed_count += 1
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error fixing device {device.device_id}: {e}"))
        
        return corrupted_count, fixed_count
    
    def scan_device_mapping(self, fix_mode):
        """Scan device_mapping for corrupted data"""
        corrupted_count = 0
        fixed_count = 0
        
        self.stdout.write("Scanning device_mapping...")
        
        for mapping in device_mapping.objects.all():
            corrupted_fields = []
            
            if '?' in str(mapping.device_type):
                corrupted_fields.append('device_type')
            if '?' in str(mapping.oem_tag):
                corrupted_fields.append('oem_tag')
            if '?' in str(mapping.discription):
                corrupted_fields.append('discription')
            if '?' in str(mapping.data_type):
                corrupted_fields.append('data_type')
            if '?' in str(mapping.units):
                corrupted_fields.append('units')
            if '?' in str(mapping.metric):
                corrupted_fields.append('metric')
            
            if corrupted_fields:
                corrupted_count += 1
                self.stdout.write(
                    f"  - Mapping ID {mapping.id}: {', '.join(corrupted_fields)}"
                )
                
                if fix_mode:
                    try:
                        with connection.cursor() as cursor:
                            update_fields = []
                            update_values = []
                            
                            for field in corrupted_fields:
                                if field == 'device_type':
                                    update_fields.append('device_type = %s')
                                    update_values.append('Unknown')
                                elif field == 'oem_tag':
                                    update_fields.append('oem_tag = %s')
                                    update_values.append('UNKNOWN_TAG')
                                elif field == 'discription':
                                    update_fields.append('discription = %s')
                                    update_values.append('Unknown Description')
                                elif field == 'data_type':
                                    update_fields.append('data_type = %s')
                                    update_values.append('STRING')
                                elif field == 'units':
                                    update_fields.append('units = %s')
                                    update_values.append('')
                                elif field == 'metric':
                                    update_fields.append('metric = %s')
                                    update_values.append('unknown')
                            
                            if update_fields:
                                update_values.append(mapping.id)
                                sql = f"UPDATE device_mapping SET {', '.join(update_fields)} WHERE id = %s"
                                cursor.execute(sql, update_values)
                                fixed_count += 1
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error fixing mapping {mapping.id}: {e}"))
        
        return corrupted_count, fixed_count
