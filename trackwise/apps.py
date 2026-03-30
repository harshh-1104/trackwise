from django.apps import AppConfig


class TrackwiseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'trackwise'

    def ready(self):
        import trackwise.signals
