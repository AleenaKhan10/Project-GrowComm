from django.apps import AppConfig


class GrowcommunityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'growcommunity'

    def ready(self):
        """Initialize dual database sync when Django starts."""
        from .dual_db_sync import connect_signals
        connect_signals()