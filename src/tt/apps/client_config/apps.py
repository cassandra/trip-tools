from django.apps import AppConfig


class ClientConfigConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tt.apps.client_config"

    def ready(self):
        import tt.apps.client_config.signals  # noqa: F401
        return
