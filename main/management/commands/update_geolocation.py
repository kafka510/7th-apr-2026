"""
Management command to update geolocation data for existing UserActivityLog records
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from main.models import UserActivityLog, ActiveUserSession
from main.activity_middleware import ActivityLoggingMiddleware
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update geolocation data for existing UserActivityLog and ActiveUserSession records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Number of records to process (default: 100)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Update records that already have location data'
        )

    def handle(self, *args, **options):
        limit = options['limit']
        force = options['force']
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting geolocation update for up to {limit} records...')
        )
        
        # Create middleware instance for geolocation methods
        middleware = ActivityLoggingMiddleware(None)
        
        # Update UserActivityLog records
        self.update_activity_logs(middleware, limit, force)
        
        # Update ActiveUserSession records
        self.update_active_sessions(middleware, limit, force)
        
        self.stdout.write(
            self.style.SUCCESS('Geolocation update completed!')
        )

    def update_activity_logs(self, middleware, limit, force):
        """Update geolocation for UserActivityLog records"""
        self.stdout.write('Updating UserActivityLog records...')
        
        # Get records without location data (or all if force)
        if force:
            queryset = UserActivityLog.objects.all()[:limit]
        else:
            queryset = UserActivityLog.objects.filter(
                country__in=['', 'Unknown', None]
            )[:limit]
        
        updated_count = 0
        for log in queryset:
            try:
                country, city, region = middleware.get_location_info(log.ip_address)
                
                if country and country not in ['Unknown', 'Error']:
                    log.country = country
                    log.city = city
                    log.region = region
                    log.save(update_fields=['country', 'city', 'region'])
                    updated_count += 1
                    
                    self.stdout.write(f'Updated {log.ip_address} -> {country}, {city}')
                
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Failed to update {log.ip_address}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Updated {updated_count} UserActivityLog records')
        )

    def update_active_sessions(self, middleware, limit, force):
        """Update geolocation for ActiveUserSession records"""
        self.stdout.write('Updating ActiveUserSession records...')
        
        # Get records without location data (or all if force)
        if force:
            queryset = ActiveUserSession.objects.all()[:limit]
        else:
            queryset = ActiveUserSession.objects.filter(
                country__in=['', 'Unknown', None]
            )[:limit]
        
        updated_count = 0
        for session in queryset:
            try:
                country, city, region = middleware.get_location_info(session.ip_address)
                
                if country and country not in ['Unknown', 'Error']:
                    session.country = country
                    session.city = city
                    session.save(update_fields=['country', 'city'])
                    updated_count += 1
                    
                    self.stdout.write(f'Updated session {session.ip_address} -> {country}, {city}')
                
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Failed to update session {session.ip_address}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Updated {updated_count} ActiveUserSession records')
        )
