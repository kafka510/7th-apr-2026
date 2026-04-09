"""
Management command to block user accounts
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.contrib.auth.models import User
from main.models import BlockedUser, UserBlockingLog
from main.middleware.realtime_ip_blocker import realtime_blocker


class Command(BaseCommand):
    help = 'Block a user account with optional expiration'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username to block')
        parser.add_argument('--reason', type=str, default='Manual block', help='Reason for blocking')
        parser.add_argument('--description', type=str, default='', help='Detailed description')
        parser.add_argument('--priority', type=str, choices=['low', 'medium', 'high', 'critical'], 
                          default='medium', help='Priority level')
        parser.add_argument('--expires-hours', type=int, help='Hours until block expires (optional)')
        parser.add_argument('--blocked-by', type=str, help='Username of admin who blocked the user')
        parser.add_argument('--force', action='store_true', help='Force block even if already blocked')

    def handle(self, *args, **options):
        username = options['username']
        reason = options['reason']
        description = options['description']
        priority = options['priority']
        expires_hours = options.get('expires_hours')
        blocked_by_username = options.get('blocked_by')
        force = options['force']

        # Check if user exists
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'User {username} not found')

        # Check if user is already blocked
        existing_block = BlockedUser.objects.filter(user=user, status='active').first()
        if existing_block and not force:
            self.stdout.write(
                self.style.WARNING(f'User {username} is already blocked. Use --force to override.')
            )
            return

        # Get blocked_by user if specified
        blocked_by = None
        if blocked_by_username:
            try:
                blocked_by = User.objects.get(username=blocked_by_username)
            except User.DoesNotExist:
                raise CommandError(f'User {blocked_by_username} not found')

        # Calculate expiration time
        expires_at = None
        if expires_hours:
            expires_at = timezone.now() + timezone.timedelta(hours=expires_hours)

        try:
            # Create or update BlockedUser record
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
                blocked_user = existing_block
                self.stdout.write(
                    self.style.WARNING(f'Updated existing block for user {username}')
                )
            else:
                blocked_user = BlockedUser.objects.create(
                    user=user,
                    reason=reason,
                    description=description,
                    priority=priority,
                    status='active',
                    blocked_by=blocked_by,
                    expires_at=expires_at,
                    last_seen=timezone.now()
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully blocked user {username}')
                )

            # Create UserBlockingLog entry
            UserBlockingLog.objects.create(
                user=user,
                block_type='manual',
                block_reason='other',
                reason_details=reason,
                ip_address='127.0.0.1',  # Local IP for manual blocks
                blocked_by=blocked_by,
                expires_at=expires_at,
                metadata={
                    'command_line': True,
                    'priority': priority,
                    'description': description
                }
            )

            # Disable the user account
            user.is_active = False
            user.save()

            # Invalidate cache to force reload
            realtime_blocker._invalidate_cache()

            # Display block information
            self.stdout.write(f'Username: {username}')
            self.stdout.write(f'Email: {user.email}')
            self.stdout.write(f'Reason: {reason}')
            self.stdout.write(f'Priority: {priority}')
            self.stdout.write(f'Status: Active (account disabled)')
            if expires_at:
                self.stdout.write(f'Expires: {expires_at}')
            else:
                self.stdout.write('Expires: Never (permanent)')
            self.stdout.write(f'Block Count: {blocked_user.block_count}')

        except Exception as e:
            raise CommandError(f'Error blocking user {username}: {str(e)}')
