"""
Custom runserver command that AUTOMATICALLY disables static file serving.
This allows our authentication middleware to handle static files.

This command is used automatically when you run: python manage.py runserver
No need to use --nostatic flag - it's disabled by default.
"""

from django.contrib.staticfiles.management.commands.runserver import Command as StaticfilesRunserverCommand
from django.core.management.commands.runserver import Command as BaseRunserverCommand


class Command(StaticfilesRunserverCommand):
    """
    Custom runserver that AUTOMATICALLY disables static file serving.
    Static files are handled by our authenticated views/middleware.
    
    Usage: python manage.py runserver (no flags needed - static serving is auto-disabled)
    
    This ensures static files always go through authentication middleware,
    both in development and production.
    """
    
    def add_arguments(self, parser):
        """Add command arguments"""
        super().add_arguments(parser)
        # Keep --nostatic flag for compatibility, but it's always disabled anyway
        parser.add_argument(
            '--nostatic',
            action='store_true',
            dest='use_static_handler',
            default=False,
            help='Disable automatic static file serving (always disabled by default in this command)',
        )
    
    def get_handler(self, *args, **options):
        """
        Override to AUTOMATICALLY disable static file serving.
        Our middleware will handle static files instead.
        """
        # CRITICAL: ALWAYS disable static file serving (automatic, no flag needed)
        options['use_static_handler'] = False
        options['use_staticfiles'] = False
        
        # Call parent but with static serving disabled
        handler = super().get_handler(*args, **options)
        return handler
    
    def run(self, *args, **options):
        """
        Override run to AUTOMATICALLY ensure static serving is disabled.
        This makes it work automatically without requiring --nostatic flag.
        """
        # ALWAYS force disable static file serving (automatic)
        options['use_static_handler'] = False
        options['use_staticfiles'] = False
        
        return super().run(*args, **options)
    
    def inner_run(self, *args, **options):
        """
        Override inner_run to ensure static serving is disabled at the handler level.
        """
        # Force disable static file serving
        options['use_static_handler'] = False
        options['use_staticfiles'] = False
        return super().inner_run(*args, **options)
