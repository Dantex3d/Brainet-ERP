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

    current_class = models.ForeignKey(
        'schools.Class',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
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