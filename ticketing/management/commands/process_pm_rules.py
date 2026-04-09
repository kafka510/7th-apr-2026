"""
Management command to process PM rules and generate tickets
Run this daily via cron or task scheduler
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import models
from django.db.models import Q
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import re

from ticketing.models import PreventiveMaintenanceRule, PreventiveMaintenanceSchedule, Ticket
from main.models import device_list, AssetList
from main.permissions import get_roles_for_capability, role_has_capability
from django.conf import settings


class Command(BaseCommand):
    help = 'Process preventive maintenance rules and generate tickets'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually creating tickets',
        )
        parser.add_argument(
            '--rule-id',
            type=int,
            help='Process only a specific rule ID',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        rule_id = options.get('rule_id')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No tickets will be created'))
        
        # Get active rules
        rules = PreventiveMaintenanceRule.objects.filter(is_active=True)
        if rule_id:
            rules = rules.filter(id=rule_id)
        
        self.stdout.write(f'Processing {rules.count()} active PM rules...\n')
        
        total_created = 0
        for rule in rules:
            self.stdout.write(f'\n📋 Processing: {rule.name} ({rule.get_rule_type_display()})')
            
            if rule.rule_type == 'date_based':
                created = self.process_date_based_rule(rule, dry_run)
            elif rule.rule_type == 'frequency_based':
                created = self.process_frequency_based_rule(rule, dry_run)
            else:
                self.stdout.write(self.style.ERROR(f'Unknown rule type: {rule.rule_type}'))
                continue
            
            total_created += created
            self.stdout.write(self.style.SUCCESS(f'✓ Created {created} tickets for this rule'))
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Total tickets created: {total_created}'))

    def process_date_based_rule(self, rule, dry_run):
        """Process date-based rules (warranty expiry, etc.)"""
        created_count = 0
        
        # Get the date field to check
        date_field = rule.date_field_name
        alert_days = rule.alert_days_before
        
        # Calculate the threshold date
        today = timezone.localdate()
        threshold_date = today + timedelta(days=alert_days)
        
        self.stdout.write(f'  Checking {date_field} expiring by {threshold_date}')
        
        # Get all devices with dates within threshold
        devices = self.get_devices_for_date_range(date_field, today, threshold_date)
        
        self.stdout.write(f'  Found {devices.count()} devices matching criteria')
        
        for device in devices:
            # Check if we already have an open ticket for this
            existing = Ticket.objects.filter(
                device_id=device,
                category=rule.category,
                metadata__pm_rule_id=rule.id,
                status__in=['raised', 'in_progress', 'submitted', 'waiting_for_approval']
            ).exists()
            
            if existing:
                continue
            
            # Get the expiry date
            raw_expiry = getattr(device, date_field)
            expiry_date = self.coerce_to_date(raw_expiry)
            if not expiry_date:
                continue

            days_until = (expiry_date - today).days
            
            if dry_run:
                self.stdout.write(f'  [DRY RUN] Would create ticket for {device.device_name} (expires in {days_until} days)')
            else:
                # Create ticket
                ticket = self.create_pm_ticket(rule, device, {
                    'expiry_date': expiry_date.isoformat(),
                    'days_until_expiry': days_until,
                    'date_field': date_field
                })
                self.stdout.write(f'  ✓ Created ticket {ticket.ticket_number} for {device.device_name}')
            
            created_count += 1
        
        return created_count

    def get_devices_for_date_range(self, field_name, start_date, end_date):
        """Return devices whose field values fall between the given dates."""
        try:
            field = device_list._meta.get_field(field_name)
        except Exception:
            return device_list.objects.none()

        filters = {f'{field_name}__isnull': False}
        if isinstance(field, models.DateTimeField):
            current_tz = timezone.get_current_timezone()
            start_dt = timezone.make_aware(datetime.combine(start_date, datetime.min.time()), current_tz)
            end_dt = timezone.make_aware(datetime.combine(end_date, datetime.max.time()), current_tz)
            filters.update({
                f'{field_name}__gte': start_dt,
                f'{field_name}__lte': end_dt,
            })
        elif isinstance(field, models.DateField):
            filters.update({
                f'{field_name}__gte': start_date,
                f'{field_name}__lte': end_date,
            })
        else:
            return device_list.objects.none()

        return device_list.objects.filter(**filters)

    def coerce_to_date(self, value):
        """Convert Date/DateTime values to a date object respecting timezones."""
        if value is None:
            return None

        if isinstance(value, datetime):
            if timezone.is_naive(value):
                value = timezone.make_aware(value, timezone.get_current_timezone())
            value = timezone.localtime(value)
            return value.date()

        return value

    def process_frequency_based_rule(self, rule, dry_run, generate_future_tickets=True, future_months=12):
        """Process frequency-based rules (calibration, PM, etc.)
        
        Args:
            rule: The PM rule to process
            dry_run: If True, don't create tickets
            generate_future_tickets: If True, generate tickets for future dates (next year)
            future_months: Number of months ahead to generate tickets (default 12)
        """
        created_count = 0
        
        start_date_field = rule.start_date_field
        frequency_field = rule.frequency_field
        
        self.stdout.write(f'  Checking {frequency_field} based on {start_date_field}')
        
        # Get all devices with frequency defined
        devices = device_list.objects.exclude(**{
            f'{frequency_field}__isnull': True
        }).exclude(**{
            f'{frequency_field}': ''
        })
        
        self.stdout.write(f'  Found {devices.count()} devices with {frequency_field} defined')
        
        today = timezone.now().date()
        end_date = today + relativedelta(months=future_months) if generate_future_tickets else today
        
        for device in devices:
            # Get or create schedule for this device
            asset = device.asset_code if hasattr(device, 'asset_code') else self.get_asset_for_device(device)
            if not asset:
                continue
                
            schedule, created = PreventiveMaintenanceSchedule.objects.get_or_create(
                rule=rule,
                device=device,
                defaults={
                    'asset': asset,
                    'next_maintenance_date': self.calculate_next_date(device, rule)
                }
            )
            
            # Update asset if it was None
            if not schedule.asset:
                schedule.asset = asset
                schedule.save()
            
            # Generate tickets for all maintenance dates up to end_date
            current_date = schedule.next_maintenance_date
            frequency_str = getattr(device, frequency_field, '')
            interval = self.parse_frequency(frequency_str)
            
            if not interval:
                continue
            
            # Generate tickets for the next year
            tickets_created_for_device = 0
            while current_date <= end_date:
                # Check if there's already a ticket for this date (within 7 days window)
                existing_ticket = Ticket.objects.filter(
                    device_id=device,
                    category=rule.category,
                    metadata__pm_rule_id=rule.id,
                    metadata__scheduled_date=current_date.isoformat(),
                    status__in=['raised', 'in_progress', 'submitted', 'waiting_for_approval', 'closed']
                ).first()
                
                if existing_ticket:
                    # Skip if ticket already exists for this date
                    current_date = self.add_interval_to_date(current_date, interval)
                    continue
                
                if dry_run:
                    self.stdout.write(f'  [DRY RUN] Would create ticket for {device.device_name} (due: {current_date})')
                else:
                    # Create ticket with scheduled date in metadata
                    ticket = self.create_pm_ticket(rule, device, {
                        'schedule_id': schedule.id,
                        'frequency': frequency_str,
                        'scheduled_date': current_date.isoformat(),
                        'last_maintenance': schedule.last_completed_date.isoformat() if schedule.last_completed_date else None
                    })
                    
                    # Update schedule to track the latest ticket
                    if not schedule.last_ticket or current_date > schedule.next_maintenance_date:
                        schedule.last_ticket = ticket
                        schedule.last_ticket_generated = timezone.now()
                    
                    # Update next_maintenance_date for future iterations
                    schedule.next_maintenance_date = self.add_interval_to_date(current_date, interval)
                    schedule.save()
                    
                    self.stdout.write(f'  ✓ Created ticket {ticket.ticket_number} for {device.device_name} (due: {current_date})')
                
                tickets_created_for_device += 1
                created_count += 1
                
                # Move to next maintenance date
                current_date = self.add_interval_to_date(current_date, interval)
                
                # Limit to prevent infinite loops (max 20 tickets per device)
                if tickets_created_for_device >= 20:
                    break
        
        return created_count
    
    def add_interval_to_date(self, date, interval):
        """Add an interval (timedelta or relativedelta) to a date"""
        if isinstance(interval, timedelta):
            return date + interval
        elif isinstance(interval, relativedelta):
            return date + interval
        else:
            return date

    def calculate_next_date(self, device, rule):
        """Calculate next maintenance date based on frequency"""
        start_date_field = rule.start_date_field
        frequency_field = rule.frequency_field
        
        # Try to get start date
        if start_date_field == 'cod':
            # Use COD from asset
            asset = self.get_asset_for_device(device)
            if asset and asset.cod:
                # Handle both date and datetime objects
                if hasattr(asset.cod, 'date'):
                    start_date = asset.cod.date()
                else:
                    start_date = asset.cod
            else:
                start_date = timezone.now().date()
        else:
            start_date = getattr(device, start_date_field, None)
            if start_date:
                start_date = start_date.date() if hasattr(start_date, 'date') else start_date
            else:
                start_date = timezone.now().date()
        
        # Get frequency
        frequency_str = getattr(device, frequency_field, '')
        interval = self.parse_frequency(frequency_str)
        
        if not interval:
            return timezone.now().date()
        
        # Calculate next date
        next_date = start_date + interval
        
        # If in the past, keep adding interval until future
        while next_date < timezone.now().date():
            next_date += interval
        
        return next_date

    def parse_frequency(self, frequency_str):
        """Parse frequency string like '6 months', '90 days', '1 year', or just '12' (assumes months)"""
        if not frequency_str:
            return None
        
        frequency_str = str(frequency_str).strip().lower()
        
        # Try to extract number and unit
        match = re.match(r'(\d+)\s*(day|days|week|weeks|month|months|year|years)?', frequency_str)
        if not match:
            return None
        
        value = int(match.group(1))
        unit = match.group(2) if match.group(2) else None
        
        # If no unit specified, assume months (common case: "12", "24", "3")
        if not unit:
            return relativedelta(months=value)
        
        # Parse with unit
        if 'day' in unit:
            return timedelta(days=value)
        elif 'week' in unit:
            return timedelta(weeks=value)
        elif 'month' in unit:
            return relativedelta(months=value)
        elif 'year' in unit:
            return relativedelta(years=value)
        
        return None

    def get_asset_for_device(self, device):
        """Get asset for a device"""
        try:
            return AssetList.objects.get(asset_code=device.parent_code)
        except AssetList.DoesNotExist:
            return None

    def create_pm_ticket(self, rule, device, metadata):
        """Create a PM ticket with auto-assignment based on role and site access"""
        # Get asset
        asset = self.get_asset_for_device(device)
        if not asset:
            self.stdout.write(self.style.WARNING(f'Could not find asset for device {device.device_name}'))
            return None
        
        # Find user to assign based on role and site access
        assigned_user = None
        if rule.assign_to_role:
            assigned_user = self.find_user_for_assignment(rule.assign_to_role, asset)
        
        # Format title and description with comprehensive device info
        context = {
            'rule_name': rule.name,
            'device_name': device.device_name,
            'device_serial': device.device_serial or 'N/A',
            'device_make': device.device_make or 'N/A',
            'device_model': device.device_model or 'N/A',
            'device_type': device.device_type or 'N/A',
            'site_name': asset.asset_name,
            'site_code': asset.asset_code,
            'country': asset.country,
            'portfolio': asset.portfolio,
            'date': timezone.now().strftime('%Y-%m-%d')
        }
        
        title = rule.title_template.format(**context)
        description = rule.description_template.format(**context)
        
        # Store comprehensive device info in metadata
        device_snapshot = {
            'device_id': device.device_id,
            'device_name': device.device_name,
            'device_serial': device.device_serial,
            'device_make': device.device_make,
            'device_model': device.device_model,
            'device_type': device.device_type,
        }
        
        # Create ticket
        ticket = Ticket.objects.create(
            title=title,
            description=description,
            asset_code=asset,
            device_id=device,
            category=rule.category,
            priority=rule.priority,
            assigned_to=assigned_user,
            created_by=rule.created_by,
            metadata={
                'pm_rule_id': rule.id,
                'pm_rule_name': rule.name,
                'auto_generated': True,
                'device_info': device_snapshot,
                **metadata
            }
        )
        
        # Send email notification if enabled
        if rule.send_email_notification:
            self.send_pm_ticket_notification(ticket, rule, assigned_user)
        
        return ticket
    
    def find_user_for_assignment(self, role, asset):
        """Find a user with the specified role who has access to the asset/site"""
        from main.models import UserProfile

        assignable_roles = get_roles_for_capability('ticketing.assignable')
        target_role = role if role in assignable_roles else None

        if target_role:
            user_profiles = UserProfile.objects.filter(role=target_role, user__is_active=True)
        else:
            user_profiles = UserProfile.objects.filter(role__in=assignable_roles, user__is_active=True)

        # Filter by site access
        for profile in user_profiles:
            # Check if user has access to this asset
            accessible_sites = profile.get_accessible_sites()
            if asset in accessible_sites or role_has_capability(profile.role, 'ticketing.view_all_sites'):
                return profile.user

        # Fallback: return first user with PM management capability if no role-specific user found
        manager_roles = get_roles_for_capability('ticketing.manage_pm_rules')
        if not manager_roles:
            manager_roles = get_roles_for_capability('ticketing.manage_settings')

        fallback_profile = UserProfile.objects.filter(role__in=manager_roles, user__is_active=True).first()
        return fallback_profile.user if fallback_profile else None
    
    def send_pm_ticket_notification(self, ticket, rule, assigned_user):
        """Send email notification for PM ticket creation"""
        try:
            from django.core.mail import send_mail
            
            recipients = []
            
            # Add assigned user
            if assigned_user and assigned_user.email:
                recipients.append(assigned_user.email)
            
            # Add ticketing managers for the site
            from main.models import UserProfile
            manager_roles = get_roles_for_capability('ticketing.manage_pm_rules')
            if not manager_roles:
                manager_roles = get_roles_for_capability('ticketing.manage_settings')

            admin_profiles = UserProfile.objects.filter(role__in=manager_roles, user__is_active=True)
            for profile in admin_profiles:
                accessible_sites = profile.get_accessible_sites()
                has_site_access = ticket.asset_code in accessible_sites
                if not has_site_access and ticket.asset_code:
                    has_site_access = role_has_capability(profile.role, 'ticketing.view_all_sites')
                if has_site_access and profile.user.email:
                    if profile.user.email not in recipients:
                        recipients.append(profile.user.email)
            
            if not recipients:
                return
            
            subject = f'[PM Alert] {ticket.ticket_number}: {ticket.title}'
            message = f'''
Automated Preventive Maintenance Ticket Created

Ticket Number: {ticket.ticket_number}
Rule: {rule.name}
Site: {ticket.asset_code.asset_name} ({ticket.asset_code.asset_code})
Device: {ticket.device_id.device_name}
  Serial: {ticket.device_id.device_serial}
  Make: {ticket.device_id.device_make}
  Model: {ticket.device_id.device_model}

Priority: {ticket.get_priority_display()}
Category: {ticket.category.name}
Assigned To: {assigned_user.username if assigned_user else 'Unassigned'}

Description:
{ticket.description}

This is an automated preventive maintenance ticket. Please complete the required maintenance activities.

View ticket: {getattr(settings, 'SITE_URL', 'http://localhost:8000')}/tickets/{ticket.id}/
'''
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                recipients,
                fail_silently=True
            )
            
            self.stdout.write(self.style.SUCCESS(f'  ✉️  Sent notification to {len(recipients)} recipient(s)'))
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  ⚠️  Failed to send notification: {str(e)}'))

