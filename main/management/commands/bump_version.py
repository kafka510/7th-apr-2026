"""
Management command to update the STATIC_VERSION for cache busting
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import os
import re
from pathlib import Path


class Command(BaseCommand):
    help = 'Bump the STATIC_VERSION in settings.py for cache busting'

    def add_arguments(self, parser):
        parser.add_argument(
            '--version',
            type=str,
            help='Specific version to set (e.g., 1.0.1)',
        )
        parser.add_argument(
            '--auto',
            action='store_true',
            help='Auto-increment the version number',
        )

    def handle(self, *args, **options):
        settings_path = Path(settings.BASE_DIR) / 'web_app' / 'settings.py'
        
        if not settings_path.exists():
            self.stdout.write(self.style.ERROR(f'Settings file not found: {settings_path}'))
            return
        
        # Read the settings file
        with open(settings_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the current STATIC_VERSION
        version_pattern = r"STATIC_VERSION\s*=\s*['\"]([^'\"]+)['\"]"
        match = re.search(version_pattern, content)
        
        if not match:
            self.stdout.write(self.style.ERROR('STATIC_VERSION not found in settings.py'))
            return
        
        current_version = match.group(1)
        self.stdout.write(f'Current version: {current_version}')
        
        # Determine new version
        if options['version']:
            new_version = options['version']
        elif options['auto']:
            # Auto-increment version
            try:
                parts = current_version.split('.')
                if len(parts) == 3:
                    major, minor, patch = parts
                    new_version = f"{major}.{minor}.{int(patch) + 1}"
                else:
                    new_version = current_version + '.1'
            except (ValueError, AttributeError):
                self.stdout.write(self.style.ERROR('Cannot auto-increment version'))
                return
        else:
            self.stdout.write(self.style.ERROR('Please specify --version or --auto'))
            return
        
        # Replace the version
        new_content = re.sub(
            version_pattern,
            f"STATIC_VERSION = '{new_version}'",
            content
        )
        
        # Write back to file
        with open(settings_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        self.stdout.write(self.style.SUCCESS(f'Version updated: {current_version} → {new_version}'))
        self.stdout.write(self.style.WARNING('Users will now get fresh static files on their next page load!'))
        self.stdout.write('')
        self.stdout.write('Next steps:')
        self.stdout.write('  1. Restart your Django server')
        self.stdout.write('  2. Users will automatically get the new version')
        self.stdout.write('  3. No browser cache clearing needed!')

