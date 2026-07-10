from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import timedelta
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
        ("bursar", "Bursar"),
        ("admin", "Admin"),
        ("superuser", "Superuser"),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="student")
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=64, blank=True, null=True, unique=True)
    email_verification_sent_at = models.DateTimeField(null=True, blank=True)
    
    # Verification code for DOS/Principal (6-digit numeric code)
    verification_code = models.CharField(max_length=6, blank=True, null=True)
    verification_code_sent_at = models.DateTimeField(null=True, blank=True)
    verification_attempts = models.IntegerField(default=0)

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

    def generate_verification_code(self):
        """Generate a 6-digit numeric verification code"""
        import random
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        self.verification_code = code
        self.verification_code_sent_at = timezone.now()
        self.verification_attempts = 0
        self.save(update_fields=["verification_code", "verification_code_sent_at", "verification_attempts"])
        return code

    def verify_code(self, code):
        """Verify the provided code. Returns (success, message)"""
        if not self.verification_code:
            return False, "No verification code requested."
        
        if self.verification_code_sent_at + timedelta(hours=1) < timezone.now():
            self.verification_code = None
            self.save(update_fields=["verification_code"])
            return False, "Verification code has expired. Request a new one."
        
        self.verification_attempts += 1
        if self.verification_attempts > 5:
            self.verification_code = None
            self.save(update_fields=["verification_code", "verification_attempts"])
            return False, "Too many failed attempts. Request a new code."
        
        if code.strip() != self.verification_code:
            self.save(update_fields=["verification_attempts"])
            return False, "Invalid verification code."
        
        self.mark_email_verified()
        return True, "Email verified successfully."

    def mark_email_verified(self):
        self.email_verified = True
        self.email_verification_token = None
        self.verification_code = None
        self.save(update_fields=["email_verified", "email_verification_token", "verification_code"])

    def __str__(self):
        return self.email