"""
Management command to block IP addresses
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from main.models import BlockedIP, IPBlockingLog
from main.middleware.realtime_ip_blocker import realtime_blocker


class Command(BaseCommand):
    help = 'Block an IP address with optional expiration'

    def add_arguments(self, parser):
        parser.add_argument('ip_address', type=str, help='IP address to block')
        parser.add_argument('--reason', type=str, default='Manual block', help='Reason for blocking')
        parser.add_argument('--description', type=str, default='', help='Detailed description')
        parser.add_argument('--priority', type=str, choices=['low', 'medium', 'high', 'critical'], 
                          default='medium', help='Priority level')
        parser.add_argument('--expires-hours', type=int, help='Hours until block expires (optional)')
        parser.add_argument('--blocked-by', type=str, help='Username of admin who blocked the IP')
        parser.add_argument('--force', action='store_true', help='Force block even if already blocked')

    def handle(self, *args, **options):
        ip_address = options['ip_address']
        reason = options['reason']
        description = options['description']
        priority = options['priority']
        expires_hours = options.get('expires_hours')
        blocked_by_username = options.get('blocked_by')
        force = options['force']

        # Check if IP is already blocked
        existing_block = BlockedIP.objects.filter(ip_address=ip_address, status='active').first()
        if existing_block and not force:
            self.stdout.write(
                self.style.WARNING(f'IP {ip_address} is already blocked. Use --force to override.')
            )
            return

        # Get blocked_by user if specified
        blocked_by = None
        if blocked_by_username:
            from django.contrib.auth.models import User
            try:
                blocked_by = User.objects.get(username=blocked_by_username)
            except User.DoesNotExist:
                raise CommandError(f'User {blocked_by_username} not found')

        # Calculate expiration time
        expires_at = None
        if expires_hours:
            expires_at = timezone.now() + timezone.timedelta(hours=expires_hours)

        try:
            # Create or update BlockedIP record
            if existing_block and force:
                existing_block.reason = reason
                existing_block.description = description
                existing_block.priority = priority
                existing_block.status = 'active'
                existing_block.blocked_by = blocked_by
                existing_block.expires_at = expires_at
                existing_block.block_count += 1
                existing_block.last_seen = timezone.now()
                existing_block.save()
                blocked_ip = existing_block
                self.stdout.write(
                    self.style.WARNING(f'Updated existing block for IP {ip_address}')
                )
            else:
                blocked_ip = BlockedIP.objects.create(
                    ip_address=ip_address,
                    reason=reason,
                    description=description,
                    priority=priority,
                    status='active',
                    blocked_by=blocked_by,
                    expires_at=expires_at,
                    last_seen=timezone.now()
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully blocked IP {ip_address}')
                )

            # Create IPBlockingLog entry
            IPBlockingLog.objects.create(
                ip_address=ip_address,
                block_type='manual',
                block_reason='other',
                reason_details=reason,
                blocked_by=blocked_by,
                expires_at=expires_at,
                metadata={
                    'command_line': True,
                    'priority': priority,
                    'description': description
                }
            )

            # Invalidate cache to force reload
            realtime_blocker._invalidate_cache()

            # Display block information
            self.stdout.write(f'IP Address: {ip_address}')
            self.stdout.write(f'Reason: {reason}')
            self.stdout.write(f'Priority: {priority}')
            self.stdout.write(f'Status: Active')
            if expires_at:
                self.stdout.write(f'Expires: {expires_at}')
            else:
                self.stdout.write('Expires: Never (permanent)')
            self.stdout.write(f'Block Count: {blocked_ip.block_count}')

        except Exception as e:
            raise CommandError(f'Error blocking IP {ip_address}: {str(e)}')
