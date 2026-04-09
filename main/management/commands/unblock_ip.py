"""
Management command to unblock IP addresses
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from main.models import BlockedIP, IPBlockingLog
from main.middleware.realtime_ip_blocker import realtime_blocker


class Command(BaseCommand):
    help = 'Unblock an IP address'

    def add_arguments(self, parser):
        parser.add_argument('ip_address', type=str, help='IP address to unblock')
        parser.add_argument('--reason', type=str, default='Manual unblock', help='Reason for unblocking')
        parser.add_argument('--unblocked-by', type=str, help='Username of admin who unblocked the IP')

    def handle(self, *args, **options):
        ip_address = options['ip_address']
        reason = options['reason']
        unblocked_by_username = options.get('unblocked_by')

        # Check if IP is blocked
        try:
            blocked_ip = BlockedIP.objects.get(ip_address=ip_address, status='active')
        except BlockedIP.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(f'IP {ip_address} is not currently blocked')
            )
            return

        # Get unblocked_by user if specified
        unblocked_by = None
        if unblocked_by_username:
            from django.contrib.auth.models import User
            try:
                unblocked_by = User.objects.get(username=unblocked_by_username)
            except User.DoesNotExist:
                raise CommandError(f'User {unblocked_by_username} not found')

        try:
            # Update BlockedIP record
            blocked_ip.status = 'inactive'
            blocked_ip.updated_at = timezone.now()
            blocked_ip.save()

            # Create IPBlockingLog entry for unblocking
            IPBlockingLog.objects.create(
                ip_address=ip_address,
                block_type='manual',
                block_reason='other',
                reason_details=f"Unblocked: {reason}",
                blocked_by=blocked_ip.blocked_by,
                status='unblocked',
                unblocked_by=unblocked_by,
                unblocked_at=timezone.now(),
                unblock_reason=reason,
                metadata={
                    'command_line': True,
                    'original_reason': blocked_ip.reason
                }
            )

            # Invalidate cache to force reload
            realtime_blocker._invalidate_cache()

            # Clear failed login attempts for users associated with this IP
            from accounts.models import LoginAttempt
            from main.models import UserBlockingLog
            
            # Find users blocked from this IP
            affected_users = UserBlockingLog.objects.filter(
                ip_address=ip_address,
                status='active'
            ).values_list('user__username', flat=True).distinct()
            
            # Clear attempts for each user
            cleared_count = 0
            for username in affected_users:
                if username:
                    LoginAttempt.clear_attempts(username)
                    cleared_count += 1
            
            if cleared_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'Cleared login attempts for {cleared_count} user(s)')
                )

            self.stdout.write(
                self.style.SUCCESS(f'Successfully unblocked IP {ip_address}')
            )
            self.stdout.write(f'Original reason: {blocked_ip.reason}')
            self.stdout.write(f'Unblock reason: {reason}')
            self.stdout.write(f'Block count: {blocked_ip.block_count}')

        except Exception as e:
            raise CommandError(f'Error unblocking IP {ip_address}: {str(e)}')
