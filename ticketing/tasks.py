"""
Celery tasks for email notifications and preventive maintenance in the ticketing system
"""
from celery import shared_task
from django.core.mail import send_mail
from django.core.management import call_command
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

from .models import Ticket, TicketEmailNotification

logger = logging.getLogger(__name__)


# ============================================================================
# EMAIL NOTIFICATION TASKS
# ============================================================================

@shared_task
def send_ticket_created_notification(ticket_id):
    """
    Send notification when a ticket is created
    Notifies assigned user (if assigned) and admin users
    """
    try:
        ticket = Ticket.objects.get(id=ticket_id, is_active=True)
        
        # Notify assigned user if ticket is assigned
        if ticket.assigned_to:
            send_ticket_assignment_email(ticket, ticket.assigned_to)
        
        # Notify watchers
        for watcher in ticket.watchers.all():
            if watcher != ticket.created_by:
                send_ticket_assignment_email(ticket, watcher)
        
        # Notify admins about new ticket
        send_ticket_created_admin_email(ticket)
        
        return f"Notifications sent for ticket {ticket.ticket_number}"
    except Ticket.DoesNotExist:
        return f"Ticket {ticket_id} not found"
    except Exception as e:
        return f"Error sending notification: {str(e)}"


@shared_task
def send_ticket_assignment_notification(ticket_id, user_id):
    """
    Send notification when a ticket is assigned to a user
    """
    try:
        from django.contrib.auth.models import User
        ticket = Ticket.objects.get(id=ticket_id, is_active=True)
        user = User.objects.get(id=user_id)
        
        send_ticket_assignment_email(ticket, user)
        return f"Assignment notification sent to {user.username}"
    except (Ticket.DoesNotExist, User.DoesNotExist) as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error sending assignment notification: {str(e)}"


@shared_task
def send_ticket_status_changed_notification(ticket_id, old_status, new_status):
    """
    Send notification when ticket status changes
    """
    try:
        ticket = Ticket.objects.get(id=ticket_id, is_active=True)
        
        # Notify assigned user
        if ticket.assigned_to:
            send_ticket_status_change_email(ticket, ticket.assigned_to, old_status, new_status)
        
        # Notify watchers
        for watcher in ticket.watchers.all():
            if watcher != ticket.assigned_to:
                send_ticket_status_change_email(ticket, watcher, old_status, new_status)
        
        # Notify creator if status changed to closed
        if new_status == 'closed' and ticket.created_by and ticket.created_by != ticket.assigned_to:
            send_ticket_status_change_email(ticket, ticket.created_by, old_status, new_status)
        
        return f"Status change notification sent for ticket {ticket.ticket_number}"
    except Ticket.DoesNotExist:
        return f"Ticket {ticket_id} not found"
    except Exception as e:
        return f"Error sending status change notification: {str(e)}"


@shared_task
def send_ticket_comment_notification(ticket_id, comment_id):
    """
    Send notification when a comment is added to a ticket
    """
    try:
        from .models import TicketComment
        ticket = Ticket.objects.get(id=ticket_id, is_active=True)
        comment = TicketComment.objects.get(id=comment_id)
        
        # Notify assigned user (if not the commenter)
        if ticket.assigned_to and ticket.assigned_to != comment.user:
            send_ticket_comment_email(ticket, comment, ticket.assigned_to)
        
        # Notify watchers (if not the commenter)
        for watcher in ticket.watchers.all():
            if watcher != comment.user and watcher != ticket.assigned_to:
                send_ticket_comment_email(ticket, comment, watcher)
        
        # Notify creator (if not the commenter and not same as assigned)
        if ticket.created_by and ticket.created_by != comment.user and ticket.created_by != ticket.assigned_to:
            send_ticket_comment_email(ticket, comment, ticket.created_by)
        
        return f"Comment notification sent for ticket {ticket.ticket_number}"
    except (Ticket.DoesNotExist, TicketComment.DoesNotExist) as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error sending comment notification: {str(e)}"


@shared_task
def send_daily_reminder_emails():
    """
    Send daily reminders for unresponded tickets
    Finds tickets assigned but not updated in last 24 hours
    """
    try:
        yesterday = timezone.now() - timedelta(days=1)
        unresponded_tickets = Ticket.objects.filter(
            assigned_to__isnull=False,
            status__in=['raised', 'in_progress'],
            updated_at__lt=yesterday
        ).exclude(assigned_to__isnull=True).select_related('assigned_to')
        
        sent_count = 0
        for ticket in unresponded_tickets:
            try:
                send_ticket_reminder_email(ticket)
                sent_count += 1
            except Exception as e:
                # Log error but continue with other tickets
                logger.error(f"Error sending reminder for ticket {ticket.ticket_number}: {str(e)}")
        
        return f"Sent {sent_count} reminder emails"
    except Exception as e:
        return f"Error in daily reminder task: {str(e)}"


# ============================================================================
# EMAIL HELPER FUNCTIONS
# ============================================================================

def send_ticket_assignment_email(ticket, user):
    """Send email when ticket is assigned to user"""
    subject = f"New Ticket Assigned: {ticket.ticket_number} - {ticket.title}"
    
    try:
        html_message = render_to_string('ticketing/emails/assignment_email.html', {
            'ticket': ticket,
            'user': user,
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        })
        
        plain_message = f"""
        A new ticket has been assigned to you:
        
        Ticket Number: {ticket.ticket_number}
        Title: {ticket.title}
        Priority: {ticket.get_priority_display()}
        Status: {ticket.get_status_display()}
        Site: {ticket.asset_code.asset_name}
        Category: {ticket.category.name}
        
        Description:
        {ticket.description}
        
        View ticket: {getattr(settings, 'SITE_URL', 'http://localhost:8000')}/tickets/{ticket.id}/
        """
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False
        )
        
        # Log notification
        TicketEmailNotification.objects.create(
            ticket=ticket,
            recipient=user,
            notification_type='ticket_assigned',
            subject=subject,
            status='sent'
        )
    except Exception as e:
        # Log failed notification
        TicketEmailNotification.objects.create(
            ticket=ticket,
            recipient=user,
            notification_type='ticket_assigned',
            subject=subject,
            status='failed',
            error_message=str(e)
        )
        raise


def send_ticket_created_admin_email(ticket):
    """Send email to admins when a new ticket is created"""
    from django.contrib.auth.models import User
    from main.models import UserProfile
    
    # Get admin users
    admin_profiles = UserProfile.objects.filter(role='admin')
    admin_users = [profile.user for profile in admin_profiles if profile.user.is_active and profile.user.email]
    
    if not admin_users:
        return
    
    subject = f"New Ticket Created: {ticket.ticket_number} - {ticket.title}"
    
    try:
        html_message = render_to_string('ticketing/emails/ticket_created_email.html', {
            'ticket': ticket,
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        })
        
        plain_message = f"""
        A new ticket has been created:
        
        Ticket Number: {ticket.ticket_number}
        Title: {ticket.title}
        Priority: {ticket.get_priority_display()}
        Created By: {ticket.created_by.username}
        Site: {ticket.asset_code.asset_name}
        Category: {ticket.category.name}
        
        Description:
        {ticket.description}
        
        View ticket: {getattr(settings, 'SITE_URL', 'http://localhost:8000')}/tickets/{ticket.id}/
        """
        
        admin_emails = [user.email for user in admin_users]
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=admin_emails,
            html_message=html_message,
            fail_silently=False
        )
        
        # Log notifications for each admin
        for admin_user in admin_users:
            TicketEmailNotification.objects.create(
                ticket=ticket,
                recipient=admin_user,
                notification_type='ticket_created',
                subject=subject,
                status='sent'
            )
    except Exception as e:
        # Log failed notifications
        for admin_user in admin_users:
            TicketEmailNotification.objects.create(
                ticket=ticket,
                recipient=admin_user,
                notification_type='ticket_created',
                subject=subject,
                status='failed',
                error_message=str(e)
            )


def send_ticket_status_change_email(ticket, user, old_status, new_status):
    """Send email when ticket status changes"""
    # Format status for display
    old_status_display = old_status.replace('_', ' ').title()
    new_status_display = new_status.replace('_', ' ').title()
    
    subject = f"Ticket Status Changed: {ticket.ticket_number} - {new_status_display}"
    
    try:
        html_message = render_to_string('ticketing/emails/status_change_email.html', {
            'ticket': ticket,
            'user': user,
            'old_status': old_status_display,
            'new_status': new_status_display,
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        })
        
        plain_message = f"""
        Ticket status has been changed:
        
        Ticket Number: {ticket.ticket_number}
        Title: {ticket.title}
        Old Status: {old_status_display}
        New Status: {new_status_display}
        
        View ticket: {getattr(settings, 'SITE_URL', 'http://localhost:8000')}/tickets/{ticket.id}/
        """
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False
        )
        
        # Log notification
        TicketEmailNotification.objects.create(
            ticket=ticket,
            recipient=user,
            notification_type='ticket_status_changed',
            subject=subject,
            status='sent'
        )
    except Exception as e:
        # Log failed notification
        TicketEmailNotification.objects.create(
            ticket=ticket,
            recipient=user,
            notification_type='ticket_status_changed',
            subject=subject,
            status='failed',
            error_message=str(e)
        )


def send_ticket_comment_email(ticket, comment, user):
    """Send email when a comment is added to a ticket"""
    subject = f"New Comment on Ticket: {ticket.ticket_number}"
    
    try:
        html_message = render_to_string('ticketing/emails/comment_email.html', {
            'ticket': ticket,
            'comment': comment,
            'user': user,
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        })
        
        plain_message = f"""
        A new comment has been added to ticket {ticket.ticket_number}:
        
        Comment by: {comment.user.username}
        Comment: {comment.comment}
        
        Ticket: {ticket.title}
        
        View ticket: {getattr(settings, 'SITE_URL', 'http://localhost:8000')}/tickets/{ticket.id}/
        """
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False
        )
        
        # Log notification
        TicketEmailNotification.objects.create(
            ticket=ticket,
            recipient=user,
            notification_type='comment_added',
            subject=subject,
            status='sent'
        )
    except Exception as e:
        # Log failed notification
        TicketEmailNotification.objects.create(
            ticket=ticket,
            recipient=user,
            notification_type='comment_added',
            subject=subject,
            status='failed',
            error_message=str(e)
        )


def send_ticket_reminder_email(ticket):
    """Send reminder email for unresponded ticket"""
    if not ticket.assigned_to or not ticket.assigned_to.email:
        return
    
    subject = f"Reminder: Unresponded Ticket {ticket.ticket_number}"
    days_since_update = ticket.days_since_last_update
    
    try:
        html_message = render_to_string('ticketing/emails/reminder_email.html', {
            'ticket': ticket,
            'days_since_update': days_since_update,
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        })
        
        plain_message = f"""
        This is a reminder about an unresponded ticket:
        
        Ticket Number: {ticket.ticket_number}
        Title: {ticket.title}
        Priority: {ticket.get_priority_display()}
        Status: {ticket.get_status_display()}
        Days Since Last Update: {days_since_update}
        
        Please update the ticket status or add a comment.
        
        View ticket: {getattr(settings, 'SITE_URL', 'http://localhost:8000')}/tickets/{ticket.id}/
        """
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[ticket.assigned_to.email],
            html_message=html_message,
            fail_silently=False
        )
        
        # Log notification
        TicketEmailNotification.objects.create(
            ticket=ticket,
            recipient=ticket.assigned_to,
            notification_type='daily_reminder',
            subject=subject,
            status='sent'
        )
    except Exception as e:
        # Log failed notification
        TicketEmailNotification.objects.create(
            ticket=ticket,
            recipient=ticket.assigned_to,
            notification_type='daily_reminder',
            subject=subject,
            status='failed',
            error_message=str(e)
        )


# ============================================================================
# PREVENTIVE MAINTENANCE TASKS
# ============================================================================

@shared_task(name='ticketing.process_pm_rules')
def process_pm_rules_task():
    """
    Celery task to process PM rules
    This should run daily
    """
    try:
        logger.info('Starting PM rules processing task')
        call_command('process_pm_rules')
        logger.info('PM rules processing completed successfully')
        return {'status': 'success', 'message': 'PM rules processed successfully'}
    except Exception as e:
        logger.error(f'Error processing PM rules: {str(e)}')
        return {'status': 'error', 'message': str(e)}


@shared_task(name='ticketing.update_pm_schedules_on_ticket_close')
def update_pm_schedule_on_close(ticket_id):
    """
    Update PM schedule when a frequency-based PM ticket is closed
    This recalculates the next maintenance date
    """
    from .models import PreventiveMaintenanceSchedule
    
    try:
        ticket = Ticket.objects.get(id=ticket_id)
        
        # Check if this is an auto-generated PM ticket
        if not ticket.metadata.get('auto_generated'):
            return
        
        schedule_id = ticket.metadata.get('schedule_id')
        if not schedule_id:
            return
        
        schedule = PreventiveMaintenanceSchedule.objects.get(id=schedule_id)
        rule = schedule.rule
        
        # Only update for frequency-based rules
        if rule.rule_type != 'frequency_based':
            return
        
        # Update last completed date to ticket closure date
        schedule.last_completed_date = ticket.closed_at.date() if ticket.closed_at else timezone.now().date()
        
        # Calculate next maintenance date from closure date
        from .management.commands.process_pm_rules import Command
        cmd = Command()
        
        # Get frequency
        frequency_field = rule.frequency_field
        frequency_str = getattr(schedule.device, frequency_field, '')
        interval = cmd.parse_frequency(frequency_str)
        
        if interval:
            schedule.next_maintenance_date = schedule.last_completed_date + interval
        
        schedule.save()
        
        logger.info(f'Updated PM schedule {schedule.id} - next maintenance: {schedule.next_maintenance_date}')
        
    except Exception as e:
        logger.error(f'Error updating PM schedule for ticket {ticket_id}: {str(e)}')
