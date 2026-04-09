"""
Django management command to clear blocking cache in real-time
This allows unblocking without restarting the application
"""

from django.core.management.base import BaseCommand
from main.middleware.realtime_ip_blocker import realtime_blocker
from main.models import BlockedIP, BlockedUser
from django.utils import timezone


class Command(BaseCommand):
    help = 'Clear blocking cache in real-time without restarting the application'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ip',
            type=str,
            help='Specific IP address to unblock',
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Specific username to unblock',
        )
        parser.add_argument(
            '--nuclear',
            action='store_true',
            help='Clear ALL blocks (nuclear option)',
        )
        parser.add_argument(
            '--reload-db',
            action='store_true',
            help='Reload blocked IPs/users from database',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔄 Clearing blocking cache in real-time...')
        )
        
        try:
            if options['nuclear']:
                # Nuclear option - clear everything
                self.clear_all_blocks()
            elif options['ip']:
                # Clear specific IP
                self.clear_ip_block(options['ip'])
            elif options['user']:
                # Clear specific user
                self.clear_user_block(options['user'])
            elif options['reload_db']:
                # Reload from database
                self.reload_from_database()
            else:
                # Show help
                self.show_help()
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error: {str(e)}')
            )

    def clear_all_blocks(self):
        """Clear all blocks (nuclear option)"""
        self.stdout.write('🚨 NUCLEAR OPTION - Clearing ALL blocks...')
        
        # Clear activity cache
        realtime_blocker.activity_cache.clear()
        
        # Invalidate cache (will reload from database on next access)
        realtime_blocker._invalidate_cache()
        
        # Deactivate all database blocks
        blocked_ips = BlockedIP.objects.filter(status='active')
        blocked_users = BlockedUser.objects.filter(status='active')
        
        ip_count = blocked_ips.count()
        user_count = blocked_users.count()
        
        blocked_ips.update(status='inactive', updated_at=timezone.now())
        blocked_users.update(status='inactive', updated_at=timezone.now())
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Cleared {ip_count} IP blocks and {user_count} user blocks'
            )
        )

    def clear_ip_block(self, ip_address):
        """Clear specific IP block"""
        self.stdout.write(f'🔓 Unblocking IP: {ip_address}')
        
        # Remove from activity cache
        if ip_address in realtime_blocker.activity_cache:
            del realtime_blocker.activity_cache[ip_address]
        
        # Invalidate cache (will reload from database on next access)
        realtime_blocker._invalidate_cache()
        
        # Deactivate database blocks
        blocked_ips = BlockedIP.objects.filter(
            ip_address=ip_address, 
            status='active'
        )
        count = blocked_ips.count()
        blocked_ips.update(status='inactive', updated_at=timezone.now())
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Unblocked IP {ip_address} ({count} blocks cleared)')
        )

    def clear_user_block(self, username):
        """Clear specific user block"""
        self.stdout.write(f'🔓 Unblocking user: {username}')
        
        # Invalidate cache (will reload from database on next access)
        realtime_blocker._invalidate_cache()
        
        # Deactivate database blocks
        blocked_users = BlockedUser.objects.filter(
            user__username=username, 
            status='active'
        )
        count = blocked_users.count()
        blocked_users.update(status='inactive', updated_at=timezone.now())
        
        # Reactivate user account
        from django.contrib.auth.models import User
        try:
            user = User.objects.get(username=username)
            user.is_active = True
            user.save()
            self.stdout.write(f'✅ Reactivated user account: {username}')
        except User.DoesNotExist:
            self.stdout.write(f'⚠️  User {username} not found')
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Unblocked user {username} ({count} blocks cleared)')
        )

    def reload_from_database(self):
        """Reload blocked IPs/users from database"""
        self.stdout.write('🔄 Reloading blocking data from database...')
        
        # Reload from database (this will update cache)
        realtime_blocker.force_reload_cache()
        
        # Get counts after reload
        blocked_ips = realtime_blocker.blocked_ips
        blocked_users = realtime_blocker.blocked_users
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Reloaded {len(blocked_ips)} IP blocks and '
                f'{len(blocked_users)} user blocks from database'
            )
        )

    def show_help(self):
        """Show usage help"""
        self.stdout.write('📖 Usage:')
        self.stdout.write('  python manage.py clear_blocking_cache --ip 192.168.1.1')
        self.stdout.write('  python manage.py clear_blocking_cache --user username')
        self.stdout.write('  python manage.py clear_blocking_cache --nuclear')
        self.stdout.write('  python manage.py clear_blocking_cache --reload-db')
