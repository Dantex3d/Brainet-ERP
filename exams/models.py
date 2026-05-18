# exams/models.py

from django.db import models

from schools.models import (
    School,
    Term,
    Subject,
    Class,
)

from students.models import Student
from teachers.models import Teacher


# =========================================================
# EXAM MODEL
# =========================================================

class Exam(models.Model):

    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE
    )

    term = models.ForeignKey(
        Term,
        on_delete=models.CASCADE
    )

    name = models.CharField(
        max_length=100
    )

    exam_type = models.CharField(
        max_length=50,
        default="Main Exam"
    )

    start_date = models.DateField()

    end_date = models.DateField()

    is_open = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.name} - {self.term.name}"


# =========================================================
# MARK MODEL
# =========================================================

class Mark(models.Model):

    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE
    )

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE
    )

    school_class = models.ForeignKey(
        Class,
        on_delete=models.CASCADE
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE
    )

    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    score = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    grade = models.CharField(
        max_length=5,
        blank=True,
        null=True
    )

    points = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=0
    )

    remarks = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        unique_together = (
            "exam",
            "student",
            "subject"
        )

        ordering = [
            "student",
            "subject"
        ]

    def __str__(self):
        return (
            f"{self.student.name} - "
            f"{self.subject.name} - "
            f"{self.score}"
        )