from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .managers import UserManager


class CustomUser(AbstractUser):
    """
    Stable ERP user model (NO circular dependencies)
    """

    username = None  # remove username completely

    email = models.EmailField(_("email address"), unique=True)

    ROLE_CHOICES = (
        ("student", "Student"),
        ("teacher", "Teacher"),
        ("dos", "DOS"),
        ("principal", "Principal"),
        ("admin", "Admin"),
        ("superuser", "Superuser"),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="student")
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=64, blank=True, null=True, unique=True)
    email_verification_sent_at = models.DateTimeField(null=True, blank=True)

    # IMPORTANT: keep this OPTIONAL to avoid circular migration crash
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users"
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def generate_email_verification_token(self):
        import secrets

        token = secrets.token_urlsafe(32)
        self.email_verification_token = token
        self.email_verification_sent_at = timezone.now()
        self.save(update_fields=["email_verification_token", "email_verification_sent_at"])
        return token

    def mark_email_verified(self):
        self.email_verified = True
        self.email_verification_token = None
        self.save(update_fields=["email_verified", "email_verification_token"])

    def __str__(self):
        return self.email