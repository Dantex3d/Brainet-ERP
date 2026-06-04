# classes/models.py
from django.db import models

class Class(models.Model):
    school = models.ForeignKey(
        "schools.School",   # ✅ string reference avoids circular import
        on_delete=models.CASCADE,
        related_name="classes_app_classes"
    )
    name = models.CharField(max_length=100)
    level = models.IntegerField()
    class_master = models.ForeignKey(
        "teachers.Teacher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mastered_classes"
    )

    def __str__(self):
        return f"{self.name} ({self.school.name})"


class Stream(models.Model):
    class_group = models.ForeignKey(
        "classes.Class",    # ✅ string reference
        on_delete=models.CASCADE,
        related_name="streams"
    )
    name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.class_group.name} - {self.name if self.name else 'Default'}"
