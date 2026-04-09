"""
Management command to reset all existing APIUser records to web-only access
This ensures existing users don't accidentally have API access
"""

from django.core.management.base import BaseCommand
from api.models import APIUser


class Command(BaseCommand):
    help = 'Reset all existing APIUser records to web_only access level'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Actually perform the update (required for execution)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        confirm = options['confirm']
        
        if not dry_run and not confirm:
            self.stdout.write(self.style.ERROR(
                'Please use --dry-run to preview changes, or --confirm to execute'
            ))
            return
        
        # Get all APIUser records
        api_users = APIUser.objects.all()
        total_count = api_users.count()
        
        if total_count == 0:
            self.stdout.write(self.style.WARNING('No APIUser records found'))
            return
        
        # Count by access level
        web_only = api_users.filter(access_level='web_only').count()
        api_only = api_users.filter(access_level='api_only').count()
        both = api_users.filter(access_level='both').count()
        
        self.stdout.write(self.style.SUCCESS(f'\nFound {total_count} APIUser records:'))
        self.stdout.write(f'  - Web Only: {web_only}')
        self.stdout.write(f'  - API Only: {api_only}')
        self.stdout.write(f'  - Both: {both}')
        
        # Calculate what will change
        to_update = api_users.exclude(access_level='web_only')
        update_count = to_update.count()
        
        if update_count == 0:
            self.stdout.write(self.style.SUCCESS('\n✅ All users already have web_only access'))
            return
        
        self.stdout.write(self.style.WARNING(f'\n{update_count} users will be updated to web_only:'))
        for user in to_update:
            self.stdout.write(f'  - {user.user.username} ({user.name}) - Current: {user.access_level}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n[DRY RUN] No changes made'))
            self.stdout.write('Run with --confirm to apply changes')
            return
        
        if confirm:
            # Update all to web_only
            updated = to_update.update(access_level='web_only')
            
            self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully updated {updated} users to web_only access'))
            self.stdout.write(self.style.WARNING(
                '\nNote: Admins can grant API access to specific users via:'
            ))
            self.stdout.write('  1. User Management page → Edit User → Change Access Level')
            self.stdout.write('  2. API Config page → Create API User → Select Access Level')

