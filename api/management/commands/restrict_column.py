"""
Management command to add column restrictions
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from api.models import APIUser, TablePermission, ColumnRestriction


class Command(BaseCommand):
    help = 'Add column restriction for an API user'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username of the Django user')
        parser.add_argument('table', type=str, help='Table name')
        parser.add_argument('column', type=str, help='Column name to restrict')
        parser.add_argument(
            '--type',
            type=str,
            choices=['hidden', 'masked'],
            default='hidden',
            help='Restriction type: hidden (exclude from results) or masked (return as null)'
        )

    def handle(self, *args, **options):
        username = options['username']
        table_name = options['table']
        column_name = options['column']
        restriction_type = options['type']

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User "{username}" does not exist'))
            return

        try:
            api_user = APIUser.objects.get(user=user)
        except APIUser.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'API user not found for "{username}"'))
            self.stdout.write('Run: python manage.py setup_api_permissions {username} --tables {table_name}')
            return

        try:
            table_permission = TablePermission.objects.get(
                api_user=api_user,
                table_name=table_name
            )
        except TablePermission.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User does not have access to table "{table_name}"'))
            self.stdout.write('Run: python manage.py setup_api_permissions {username} --tables {table_name}')
            return

        # Create or update column restriction
        restriction, created = ColumnRestriction.objects.get_or_create(
            table_permission=table_permission,
            column_name=column_name,
            defaults={'restriction_type': restriction_type}
        )

        if not created:
            restriction.restriction_type = restriction_type
            restriction.save()
            self.stdout.write(self.style.WARNING(f'Updated existing restriction'))

        self.stdout.write(self.style.SUCCESS(
            f'Column "{column_name}" in table "{table_name}" is now {restriction_type} '
            f'for user "{username}"'
        ))

