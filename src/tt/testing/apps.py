from django.apps import AppConfig


class TestingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tt.testing'
    verbose_name = 'Testing Utilities'
