from django.apps import AppConfig


class ConfigAssetsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.config_assets'
    label = 'config_assets'

    def ready(self):
        import apps.config_assets.signals
