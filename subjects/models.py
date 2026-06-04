from django.db import models


class Subject(models.Model):
    school = models.ForeignKey("schools.School", on_delete=models.CASCADE)

    name = models.CharField(max_length=100)

    short_name = models.CharField(max_length=20)
    code = models.IntegerField()

    def __str__(self):
        return f"{self.name} ({self.short_name})"


class ClassSubject(models.Model):
    school = models.ForeignKey("schools.School", on_delete=models.CASCADE)
    class_name = models.ForeignKey("classes.Class", on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)

    teacher = models.ForeignKey(
        "teachers.Teacher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    is_optional = models.BooleanField(default=False)

    class Meta:
        unique_together = ("class_name", "subject")

    def __str__(self):
        return f"{self.class_name} - {self.subject}"


class StudentSubject(models.Model):
    """Track which subjects a student is enrolled in"""
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="enrolled_subjects"
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE
    )
    class_subject = models.ForeignKey(
        ClassSubject,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "subject")

    def __str__(self):
        return f"{self.student.name} - {self.subject.name}"
