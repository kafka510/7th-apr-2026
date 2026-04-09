from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        # Import signal handlers that keep permission caches in sync
        try:
            import accounts.signals  # noqa: F401
        except Exception:
            # Signals are best-effort; avoid crashing app start if migrations not ready
            pass
