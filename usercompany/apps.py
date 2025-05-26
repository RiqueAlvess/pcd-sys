from django.apps import AppConfig


class UsercompanyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'usercompany'
    verbose_name = 'User Company - Dashboard Empresa'
    
    def ready(self):
        import usercompany.signals