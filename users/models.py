from django.contrib.auth.models import AbstractUser
from django.db import models
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
        ("admin", "Admin"),
        ("superuser", "Superuser"),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="student")

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

    def __str__(self):
        return self.email