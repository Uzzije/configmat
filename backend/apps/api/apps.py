"""
Django app configuration for Public API.
"""

from django.apps import AppConfig


class ApiConfig(AppConfig):
    """Configuration for the Public API app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.api'
    verbose_name = 'Public API'
    
    def ready(self):
        """
        Import signal handlers when app is ready.
        """
        # Import signals here if needed
        pass
