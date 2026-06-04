from django.db import models
from django.conf import settings


class Student(models.Model):

    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_profile'
    )

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE
    )

    admission_number = models.CharField(
        max_length=30,
        unique=True
    )

    name = models.CharField(max_length=200)

    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES
    )

    # ✅ FIXED: point to classes.Class instead of schools.Class
    current_class = models.ForeignKey(
        'classes.Class',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students'
    )
        
    stream = models.ForeignKey(
        "classes.Stream",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students"

    )

    dormitory = models.ForeignKey(
        'schools.Dormitory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    parent_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.admission_number})"

class StudentLoginLog(models.Model):
    
    STATUS_CHOICES = (
        ("success", "Success"),
        ("failed", "Failed"),
    )

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    username = models.CharField(max_length=255)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES
    )

    ip_address = models.CharField(
        max_length=120,
        null=True,
        blank=True
    )

    user_agent = models.TextField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.username} - {self.status}"