"""
Management command to list available device fields for PM rules
Helps admins see what fields are available when creating rules
"""
from django.core.management.base import BaseCommand
from main.models import device_list


class Command(BaseCommand):
    help = 'List available device_list fields for PM rule configuration'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Available Device List Fields ===\n'))
        
        # Get one device to inspect
        sample_device = device_list.objects.first()
        if not sample_device:
            self.stdout.write(self.style.WARNING('No devices found in database'))
            return
        
        # Date fields
        self.stdout.write(self.style.HTTP_INFO('📅 DATE FIELDS (for date-based rules):'))
        date_fields = [
            'equipment_warranty_start_date',
            'equipment_warranty_expire_date',
            'epc_warranty_start_date',
            'epc_warranty_expire_date',
        ]
        
        for field in date_fields:
            value = getattr(sample_device, field, None)
            status = '✓' if value else '✗'
            self.stdout.write(f'  {status} {field}: {value or "Not set"}')
        
        # Frequency fields
        self.stdout.write(self.style.HTTP_INFO('\n⏱️  FREQUENCY FIELDS (for frequency-based rules):'))
        frequency_fields = [
            'calibration_frequency',
            'pm_frequency',
            'visual_inspection_frequency',
        ]
        
        for field in frequency_fields:
            value = getattr(sample_device, field, None)
            status = '✓' if value else '✗'
            self.stdout.write(f'  {status} {field}: {value or "Not set"}')
        
        # Start date options
        self.stdout.write(self.style.HTTP_INFO('\n🏁 START DATE OPTIONS:'))
        self.stdout.write('  • Use "cod" to reference COD from AssetList')
        for field in date_fields:
            self.stdout.write(f'  • {field}')
        
        # Sample device info
        self.stdout.write(self.style.HTTP_INFO(f'\n📊 Sample Device: {sample_device.device_name}'))
        self.stdout.write(f'  Device ID: {sample_device.device_id}')
        self.stdout.write(f'  Type: {sample_device.device_type}')
        self.stdout.write(f'  Make: {sample_device.device_make}')
        self.stdout.write(f'  Model: {sample_device.device_model}')
        
        # Count statistics
        total_devices = device_list.objects.count()
        self.stdout.write(self.style.SUCCESS(f'\n✅ Total devices in system: {total_devices}'))
        
        # Check how many have each frequency field populated
        self.stdout.write(self.style.HTTP_INFO('\nFrequency Field Population:'))
        for field in frequency_fields:
            count = device_list.objects.exclude(**{f'{field}__isnull': True}).exclude(**{field: ''}).count()
            percentage = (count / total_devices * 100) if total_devices > 0 else 0
            self.stdout.write(f'  {field}: {count}/{total_devices} ({percentage:.1f}%)')

