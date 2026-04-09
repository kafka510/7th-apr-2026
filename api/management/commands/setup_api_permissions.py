"""
Management command to setup API permissions for users
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from api.models import APIUser, TablePermission, ColumnRestriction


class Command(BaseCommand):
    help = 'Setup API permissions for a user'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username of the Django user')
        parser.add_argument('--tables', type=str, help='Comma-separated list of tables to grant access to')
        parser.add_argument('--all-tables', action='store_true', help='Grant access to all available tables')
        parser.add_argument('--rate-limit-minute', type=int, default=60, help='Requests per minute limit')
        parser.add_argument('--rate-limit-hour', type=int, default=1000, help='Requests per hour limit')
        parser.add_argument('--rate-limit-day', type=int, default=10000, help='Requests per day limit')
        parser.add_argument('--max-records', type=int, default=1000, help='Max records per request')
        parser.add_argument('--allowed-ips', type=str, help='Comma-separated list of allowed IP addresses')

    def handle(self, *args, **options):
        username = options['username']
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User "{username}" does not exist'))
            return

        # Create or get APIUser
        api_user, created = APIUser.objects.get_or_create(
            user=user,
            defaults={
                'name': f"{user.username}'s API Access",
                'description': 'Configured via management command',
                'status': 'active',
                'rate_limit_per_minute': options['rate_limit_minute'],
                'rate_limit_per_hour': options['rate_limit_hour'],
                'rate_limit_per_day': options['rate_limit_day']
            }
        )

        if not created:
            # Update existing user
            api_user.rate_limit_per_minute = options['rate_limit_minute']
            api_user.rate_limit_per_hour = options['rate_limit_hour']
            api_user.rate_limit_per_day = options['rate_limit_day']
            api_user.save()
            self.stdout.write(self.style.WARNING(f'Updated existing API user for "{username}"'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Created API user for "{username}"'))

        # Set IP restrictions
        if options['allowed_ips']:
            api_user.allowed_ips = options['allowed_ips']
            api_user.save()
            self.stdout.write(self.style.SUCCESS(f'Set allowed IPs: {options["allowed_ips"]}'))

        # Define available tables (from main app)
        available_tables = [
            'AssetList',
            'kpis',
            'device_list',
            'device_mapping',
            'budget_values',
            'ic_budget',
            'timeseries_data',
            'YieldData',
            'BESSData',
            'AOCData',
            'ICEData',
            'ICVSEXVSCURData',
            'MapData',
            'MinamataStringLossData',
            'ActualGenerationDailyData',
            'ExpectedBudgetDailyData',
            'BudgetGIIDailyData',
            'ActualGIIDailyData',
            'ICApprovedBudgetDailyData',
            'LossCalculationData',
            'RealTimeKPI'
        ]

        # Determine tables to grant access to
        if options['all_tables']:
            tables_to_grant = available_tables
            self.stdout.write(self.style.SUCCESS(f'Granting access to all {len(tables_to_grant)} tables'))
        elif options['tables']:
            tables_to_grant = [t.strip() for t in options['tables'].split(',')]
            self.stdout.write(self.style.SUCCESS(f'Granting access to {len(tables_to_grant)} tables'))
        else:
            self.stdout.write(self.style.ERROR('Please specify --tables or --all-tables'))
            return

        # Grant table permissions
        for table_name in tables_to_grant:
            permission, created = TablePermission.objects.get_or_create(
                api_user=api_user,
                table_name=table_name,
                defaults={
                    'can_read': True,
                    'can_filter': True,
                    'can_aggregate': True,
                    'max_records_per_request': options['max_records']
                }
            )
            
            if created:
                self.stdout.write(f'  ✓ Granted access to {table_name}')
            else:
                self.stdout.write(f'  - Already has access to {table_name}')

        self.stdout.write(self.style.SUCCESS(f'\nAPI setup complete for "{username}"'))
        self.stdout.write('\nNext steps:')
        self.stdout.write('1. User should go to /api/dashboard/ to generate an API key')
        self.stdout.write('2. User should read the documentation at /static/API_DOCUMENTATION.md')

