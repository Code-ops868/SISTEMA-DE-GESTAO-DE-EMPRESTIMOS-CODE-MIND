from django.apps import AppConfig

class MicrocreditoAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'microcredito_app'
    
    def ready(self):
        import microcredito_app.signals  # ← PRECISA TER ESTA LINHA