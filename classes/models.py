# classes/models.py
from django.db import models
from schools.models import School


class Class(models.Model):
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="classes_app_classes"   # ✅ unique name
    )
    name = models.CharField(max_length=100)
    level = models.IntegerField()

    def __str__(self):
        return f"{self.name} ({self.school.name})"

class Stream(models.Model):
    class_group = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name="streams"
    )
    name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.class_group.name} - {self.name if self.name else 'Default'}"
