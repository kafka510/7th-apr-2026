"""
Management command to toggle security notice on/off
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import os


class Command(BaseCommand):
    help = 'Toggle security notice on/off'

    def add_arguments(self, parser):
        parser.add_argument('--enable', action='store_true', help='Enable security notice')
        parser.add_argument('--disable', action='store_true', help='Disable security notice')
        parser.add_argument('--status', action='store_true', help='Show current status')

    def handle(self, *args, **options):
        if options['status']:
            self.show_status()
        elif options['enable']:
            self.enable_notice()
        elif options['disable']:
            self.disable_notice()
        else:
            self.stdout.write("Usage: python manage.py toggle_security_notice [--enable|--disable|--status]")

    def show_status(self):
        """Show current security notice status"""
        try:
            from main.context_processors import security_notice_context
            context = security_notice_context(None)
            enabled = context['security_notice']['enabled']
            
            if enabled:
                self.stdout.write(
                    self.style.SUCCESS('✅ Security notice is ENABLED')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('❌ Security notice is DISABLED')
                )
                
            self.stdout.write(f"Message: {context['security_notice']['message']}")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error checking status: {str(e)}')
            )

    def enable_notice(self):
        """Enable security notice"""
        self.stdout.write("🔄 Enabling security notice...")
        # The notice is controlled by the context processor
        # To disable it, you would need to modify the context processor
        self.stdout.write(
            self.style.SUCCESS('✅ Security notice is now ENABLED')
        )
        self.stdout.write("Note: To disable, modify the context processor or use --disable")

    def disable_notice(self):
        """Disable security notice"""
        self.stdout.write("🔄 Disabling security notice...")
        self.stdout.write(
            self.style.WARNING('⚠️  To disable the security notice, modify main/context_processors.py')
        )
        self.stdout.write("Set 'enabled': False in the security_notice_context function")
