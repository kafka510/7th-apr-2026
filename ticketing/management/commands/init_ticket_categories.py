"""
Management command to initialize default ticket categories and loss categories
"""
from django.core.management.base import BaseCommand
from ticketing.models import TicketCategory, LossCategory


class Command(BaseCommand):
    help = 'Initialize default ticket categories and loss categories'

    def handle(self, *args, **options):
        # Create default ticket categories
        ticket_categories = [
            {'name': 'Preventive Maintenance', 'description': 'Scheduled maintenance to prevent issues', 'display_order': 1},
            {'name': 'Corrective Maintenance', 'description': 'Maintenance to fix existing issues', 'display_order': 2},
            {'name': 'Others', 'description': 'Other maintenance activities', 'display_order': 3},
        ]
        
        for cat_data in ticket_categories:
            category, created = TicketCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'description': cat_data['description'],
                    'display_order': cat_data['display_order'],
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created ticket category: {category.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Ticket category already exists: {category.name}')
                )
        
        # Create default loss categories
        loss_categories = [
            {'name': 'Grid Outage', 'description': 'Loss due to grid power outage', 'display_order': 1},
            {'name': 'Curtailment', 'description': 'Loss due to grid curtailment', 'display_order': 2},
            {'name': 'Equipment Breakdown', 'description': 'Loss due to equipment failure', 'display_order': 3},
            {'name': 'Others', 'description': 'Other loss categories', 'display_order': 4},
        ]
        
        for cat_data in loss_categories:
            category, created = LossCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'description': cat_data['description'],
                    'display_order': cat_data['display_order'],
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created loss category: {category.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Loss category already exists: {category.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS('Successfully initialized ticket and loss categories!')
        )

