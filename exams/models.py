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
    
    EXAM_TYPES = (
        ("OPENING", "Opening Exam"),
        ("MIDTERM", "Midterm Exam"),
        ("END_TERM", "End Term Exam"),
        ("CAT", "CAT"),
        ("FINAL", "Final"),
    )

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
        max_length=20,
        choices=EXAM_TYPES
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.name} - {self.exam_type}"

# =========================================================
# EXAM SUBJECTS
# =========================================================

class ExamSubject(models.Model):

    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="exam_subjects"
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE
    )

    class Meta:
        unique_together = (
            "exam",
            "subject"
        )

    def __str__(self):
        return f"{self.exam.name} - {self.subject.name}"
# =========================================================
# MARK MODEL
# =========================================================

class Mark(models.Model):
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE
    )

    term = models.ForeignKey(   # ✅ new field
        Term,
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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (
            "exam",
            "term",       # ✅ include term in uniqueness
            "student",
            "subject"
        )
        ordering = ["student", "subject"]

    def __str__(self):
        return f"{self.student.name} - {self.subject.name} - {self.score}"
