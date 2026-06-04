from django.db import models
from schools.models import Class
from django.conf import settings
from subjects.models import Subject
class Teacher(models.Model):
    
    ROLE_CHOICES = (
        ("subject", "Subject Teacher"),
        ("class", "Class Teacher"),
        ("both", "Class + Subject Teacher"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="teachers"
    )

    name = models.CharField(max_length=100)

    email = models.EmailField()

    phone = models.CharField(max_length=20)

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="subject"
    )

    date_joined = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.name
    
class ClassTeacherAssignment(models.Model):
    
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE
    )

    class_obj = models.ForeignKey(
        "classes.Class",
        on_delete=models.CASCADE
    )

    stream = models.ForeignKey(
        "classes.Stream",
        on_delete=models.CASCADE
    )

    teacher = models.ForeignKey(
        "teachers.Teacher",
        on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("class_obj", "stream")
        
class TeacherSubjectAssignment(models.Model):
    
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE
    )

    class_obj = models.ForeignKey(
        "classes.Class",
        on_delete=models.CASCADE
    )

    stream = models.ForeignKey(
        "classes.Stream",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    subject = models.ForeignKey(
        "subjects.Subject",
        on_delete=models.CASCADE
    )

    teacher = models.ForeignKey(
        "teachers.Teacher",
        on_delete=models.CASCADE
    )

    class Meta:
        unique_together = (
            "class_obj",
            "stream",
            "subject"
        )            