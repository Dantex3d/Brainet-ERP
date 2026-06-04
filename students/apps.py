from django.apps import AppConfig


class StudentsConfig(AppConfig):
    name = 'students'
    
    def ready(self):
        """Import signals when app is ready"""
        import students.signals
