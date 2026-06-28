# schools/backends.py
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from .models import DirectorOfStudies

class DOSBackend(BaseBackend):
    def authenticate(self, request, email=None, password=None):
        try:
            dos = DirectorOfStudies.objects.get(email=email)
            if dos.check_password(password):
                # Return a Django User object for session handling
                user, created = User.objects.get_or_create(
                    username=dos.email,
                    defaults={'email': dos.email}
                )
                return user
        except DirectorOfStudies.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
