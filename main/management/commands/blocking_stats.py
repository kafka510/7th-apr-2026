"""
Management command to show blocking statistics
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count, Q
from main.models import BlockedIP, BlockedUser, IPBlockingLog, UserBlockingLog
from main.middleware.realtime_ip_blocker import realtime_blocker


class Command(BaseCommand):
    help = 'Show IP and user blocking statistics'

    def add_arguments(self, parser):
        parser.add_argument('--detailed', action='store_true', help='Show detailed statistics')
        parser.add_argument('--hours', type=int, default=24, help='Hours to look back for recent activity')

    def handle(self, *args, **options):
        detailed = options['detailed']
        hours = options['hours']
        
        # Get time range
        since = timezone.now() - timezone.timedelta(hours=hours)
        
        self.stdout.write(self.style.SUCCESS('=== BLOCKING STATISTICS ===\n'))
        
        # Current active blocks
        active_ips = BlockedIP.objects.filter(status='active')
        active_users = BlockedUser.objects.filter(status='active')
        
        self.stdout.write(f'Active Blocked IPs: {active_ips.count()}')
        self.stdout.write(f'Active Blocked Users: {active_users.count()}\n')
        
        # Recent activity
        recent_ip_blocks = IPBlockingLog.objects.filter(blocked_at__gte=since)
        recent_user_blocks = UserBlockingLog.objects.filter(blocked_at__gte=since)
        
        self.stdout.write(f'IP Blocks in last {hours}h: {recent_ip_blocks.count()}')
        self.stdout.write(f'User Blocks in last {hours}h: {recent_user_blocks.count()}\n')
        
        # Block reasons breakdown
        ip_reasons = recent_ip_blocks.values('block_reason').annotate(count=Count('id')).order_by('-count')
        user_reasons = recent_user_blocks.values('block_reason').annotate(count=Count('id')).order_by('-count')
        
        self.stdout.write('Top IP Block Reasons:')
        for reason in ip_reasons[:5]:
            self.stdout.write(f'  {reason["block_reason"]}: {reason["count"]}')
        
        self.stdout.write('\nTop User Block Reasons:')
        for reason in user_reasons[:5]:
            self.stdout.write(f'  {reason["block_reason"]}: {reason["count"]}')
        
        if detailed:
            self.stdout.write('\n=== DETAILED STATISTICS ===\n')
            
            # Block types
            ip_types = recent_ip_blocks.values('block_type').annotate(count=Count('id'))
            user_types = recent_user_blocks.values('block_type').annotate(count=Count('id'))
            
            self.stdout.write('IP Block Types:')
            for block_type in ip_types:
                self.stdout.write(f'  {block_type["block_type"]}: {block_type["count"]}')
            
            self.stdout.write('\nUser Block Types:')
            for block_type in user_types:
                self.stdout.write(f'  {block_type["block_type"]}: {block_type["count"]}')
            
            # Geographic distribution
            ip_countries = recent_ip_blocks.exclude(country='').values('country').annotate(count=Count('id')).order_by('-count')
            if ip_countries:
                self.stdout.write('\nTop Countries (IP blocks):')
                for country in ip_countries[:10]:
                    self.stdout.write(f'  {country["country"]}: {country["count"]}')
            
            # Priority distribution
            ip_priorities = active_ips.values('priority').annotate(count=Count('id'))
            user_priorities = active_users.values('priority').annotate(count=Count('id'))
            
            self.stdout.write('\nActive IP Block Priorities:')
            for priority in ip_priorities:
                self.stdout.write(f'  {priority["priority"]}: {priority["count"]}')
            
            self.stdout.write('\nActive User Block Priorities:')
            for priority in user_priorities:
                self.stdout.write(f'  {priority["priority"]}: {priority["count"]}')
            
            # Expired blocks
            expired_ips = BlockedIP.objects.filter(
                Q(expires_at__lt=timezone.now()) | Q(status='inactive')
            ).count()
            expired_users = BlockedUser.objects.filter(
                Q(expires_at__lt=timezone.now()) | Q(status='inactive')
            ).count()
            
            self.stdout.write(f'\nExpired/Inactive IP Blocks: {expired_ips}')
            self.stdout.write(f'Expired/Inactive User Blocks: {expired_users}')
        
        # Realtime blocker stats
        try:
            stats = realtime_blocker.get_blocking_stats()
            self.stdout.write('\n=== REALTIME BLOCKER STATS ===')
            self.stdout.write(f'Tracked IPs: {stats.get("tracked_ips", 0)}')
            self.stdout.write(f'Company IPs Protected: {stats.get("company_ips_protected", 0)}')
            if 'recent_blocks_24h' in stats:
                self.stdout.write(f'Recent Blocks (24h): {stats["recent_blocks_24h"]}')
        except Exception as e:
            self.stdout.write(f'\nError getting realtime stats: {e}')
        
        self.stdout.write('\n=== END STATISTICS ===')
