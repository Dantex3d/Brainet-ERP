# teachers/models.py
from django.db import models
from schools.models import School, Class

class Teacher(models.Model):
    ROLE_CHOICES = [
        ('subject', 'Subject Teacher'),
        ('class', 'Class Teacher'),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    subject = models.CharField(max_length=100, blank=True, null=True)

    # ✅ Add related_name to avoid clash
    assigned_class = models.ForeignKey(
        Class,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_teachers"
    )

    is_active = models.BooleanField(default=True)
    date_joined = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.role}) - {self.school.name}"
