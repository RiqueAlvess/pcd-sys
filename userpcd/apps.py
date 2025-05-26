from django.apps import AppConfig


class UserpcdConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'userpcd'
    verbose_name = 'User PCD - Dashboard PCD'
    
    def ready(self):
        import userpcd.signals