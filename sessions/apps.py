from django.apps import AppConfig


class SessionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sessions'
    verbose_name = 'Charging Sessions'
    label = 'charging_sessions'
