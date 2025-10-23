from django.apps import AppConfig
from django.db.models.signals import post_migrate


class ConfigConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tt.apps.config"
    
    def ready(self):
        from tt.apps.config.signals import SettingsInitializer

        # Populate the settings for all apps discovered to need them.
        #
        # We have some evidence and a theory that this signal might be
        # missed on migrations, or does not always fire when we need it
        # to.  To safeguard against this, we have built a custom command
        # "sync_settings" that is now part of the deployment workflow.  It
        # does the same step of calling this initializer.  For now, we do
        # not think there is any harm in retaining this original signal.
        # The initializer is idempotent.
        #
        post_migrate.connect( lambda sender, **kwargs: SettingsInitializer().run( sender, **kwargs ),
                              sender = self )
        return
    
