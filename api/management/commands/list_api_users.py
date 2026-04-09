"""
Management command to list all API users and their permissions
"""

from django.core.management.base import BaseCommand
from api.models import APIUser, APIKey, TablePermission


class Command(BaseCommand):
    help = 'List all API users and their permissions'

    def handle(self, *args, **options):
        api_users = APIUser.objects.all()

        if not api_users.exists():
            self.stdout.write(self.style.WARNING('No API users found'))
            return

        for api_user in api_users:
            self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
            self.stdout.write(self.style.SUCCESS(f'API User: {api_user.name}'))
            self.stdout.write(self.style.SUCCESS(f'{"="*60}'))
            self.stdout.write(f'Django User: {api_user.user.username}')
            self.stdout.write(f'Status: {api_user.status}')
            self.stdout.write(f'Total Requests: {api_user.total_requests}')
            self.stdout.write(f'Last Request: {api_user.last_request_at or "Never"}')
            
            self.stdout.write(f'\nRate Limits:')
            self.stdout.write(f'  - Per Minute: {api_user.rate_limit_per_minute}')
            self.stdout.write(f'  - Per Hour: {api_user.rate_limit_per_hour}')
            self.stdout.write(f'  - Per Day: {api_user.rate_limit_per_day}')

            if api_user.allowed_ips:
                self.stdout.write(f'\nAllowed IPs: {api_user.allowed_ips}')

            # List API keys
            api_keys = APIKey.objects.filter(api_user=api_user)
            if api_keys.exists():
                self.stdout.write(f'\nAPI Keys ({api_keys.count()}):')
                for key in api_keys:
                    status_color = self.style.SUCCESS if key.status == 'active' else self.style.WARNING
                    self.stdout.write(status_color(
                        f'  - {key.name} ({key.key_prefix}...) '
                        f'[{key.status}] - {key.total_requests} requests'
                    ))

            # List table permissions
            permissions = TablePermission.objects.filter(api_user=api_user)
            if permissions.exists():
                self.stdout.write(f'\nTable Permissions ({permissions.count()}):')
                for perm in permissions:
                    restrictions = perm.column_restrictions.count()
                    rest_str = f' [{restrictions} restricted columns]' if restrictions > 0 else ''
                    self.stdout.write(
                        f'  - {perm.table_name}: '
                        f'Read={perm.can_read}, Filter={perm.can_filter}, '
                        f'Aggregate={perm.can_aggregate}, '
                        f'Max={perm.max_records_per_request}{rest_str}'
                    )
            else:
                self.stdout.write(self.style.WARNING('\nNo table permissions configured'))

