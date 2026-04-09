from django.apps import AppConfig


class DataCollectionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'data_collection'
    verbose_name = 'Data Collection'

    def ready(self) -> None:
        # Celery signal: optional completion email for user-initiated tasks (see user_task_completion_email).
        import data_collection.celery_signals  # noqa: F401
