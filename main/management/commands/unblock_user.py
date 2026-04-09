"""
Management command to unblock user accounts
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.contrib.auth.models import User
from main.models import BlockedUser, UserBlockingLog
from main.middleware.realtime_ip_blocker import realtime_blocker


class Command(BaseCommand):
    help = 'Unblock a user account'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username to unblock')
        parser.add_argument('--reason', type=str, default='Manual unblock', help='Reason for unblocking')
        parser.add_argument('--unblocked-by', type=str, help='Username of admin who unblocked the user')

    def handle(self, *args, **options):
        username = options['username']
        reason = options['reason']
        unblocked_by_username = options.get('unblocked_by')

        # Check if user exists
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'User {username} not found')

        # Check if user is blocked - get ALL active BlockedUser records
        active_blocked_users = BlockedUser.objects.filter(user=user, status='active')
        blocked_user = active_blocked_users.first()
        
        if not blocked_user:
            # Check if there are any inactive records (user was previously blocked)
            inactive_blocked = BlockedUser.objects.filter(user=user, status='inactive')
            if inactive_blocked.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f'User {username} is not currently blocked, but has {inactive_blocked.count()} '
                        f'inactive BlockedUser record(s). User account status: {"Active" if user.is_active else "Inactive"}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'User {username} is not currently blocked')
                )
            return
        
        # Check for multiple active records (shouldn't happen, but handle it)
        if active_blocked_users.count() > 1:
            self.stdout.write(
                self.style.WARNING(
                    f'⚠️  WARNING: User {username} has {active_blocked_users.count()} active BlockedUser records. '
                    f'All will be deactivated.'
                )
            )

        # Get unblocked_by user if specified
        unblocked_by = None
        if unblocked_by_username:
            try:
                unblocked_by = User.objects.get(username=unblocked_by_username)
            except User.DoesNotExist:
                raise CommandError(f'User {unblocked_by_username} not found')

        try:
            # Update ALL active BlockedUser records (handle multiple records)
            deactivated_count = active_blocked_users.update(
                status='inactive',
                updated_at=timezone.now()
            )
            
            # Get the primary blocked_user for logging
            blocked_user = active_blocked_users.first()

            # Create UserBlockingLog entry for unblocking
            UserBlockingLog.objects.create(
                user=user,
                block_type='manual',
                block_reason='other',
                reason_details=f"Unblocked: {reason}",
                ip_address='127.0.0.1',  # Local IP for manual blocks
                blocked_by=blocked_user.blocked_by,
                status='unblocked',
                unblocked_by=unblocked_by,
                unblocked_at=timezone.now(),
                unblock_reason=reason,
                metadata={
                    'command_line': True,
                    'original_reason': blocked_user.reason
                }
            )

            # Reactivate the user account
            user.is_active = True
            user.save()

            # Clear failed login attempts from database
            from accounts.models import LoginAttempt
            cleared_attempts = LoginAttempt.objects.filter(username=username, successful=False).count()
            LoginAttempt.clear_attempts(username)

            # Invalidate cache to force reload
            realtime_blocker._invalidate_cache()
            
            # Verify unblocking worked
            realtime_blocker.force_reload_cache()
            is_still_blocked = realtime_blocker.is_user_blocked(username)
            
            # Log the unblocking action
            import logging
            logger = logging.getLogger(__name__)
            logger.info(
                f"User {username} unblocked by {unblocked_by_username or 'command line'}. "
                f"Deactivated {deactivated_count} BlockedUser record(s), cleared {cleared_attempts} failed attempts. "
                f"User still blocked in system: {is_still_blocked}"
            )

            self.stdout.write(
                self.style.SUCCESS(f'Successfully unblocked user {username}')
            )
            self.stdout.write(f'  - Deactivated {deactivated_count} BlockedUser record(s)')
            self.stdout.write(f'  - Cleared {cleared_attempts} failed login attempt(s)')
            self.stdout.write(f'  - User account reactivated: {user.is_active}')
            if blocked_user:
                self.stdout.write(f'  - Original reason: {blocked_user.reason}')
                self.stdout.write(f'  - Block count: {blocked_user.block_count}')
            self.stdout.write(f'  - Unblock reason: {reason}')
            self.stdout.write(f'  - Verification: User still blocked in system: {is_still_blocked}')
            
            if is_still_blocked:
                self.stdout.write(
                    self.style.WARNING(
                        '⚠️  WARNING: User is still marked as blocked in the system. '
                        'This may indicate a cache synchronization issue. Please verify manually.'
                    )
                )

        except Exception as e:
            raise CommandError(f'Error unblocking user {username}: {str(e)}')
