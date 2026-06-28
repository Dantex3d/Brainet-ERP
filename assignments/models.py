from django.db import models
from teachers.models import Teacher


# =========================
# ASSIGNMENT MODEL
# =========================
class Assignment(models.Model):

    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE
    )

    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE
    )

    class_assigned = models.ForeignKey(
        "classes.Class",
        on_delete=models.CASCADE
    )

    subject = models.ForeignKey(
        "subjects.Subject",
        on_delete=models.CASCADE
    )

    title = models.CharField(max_length=200)

    instructions = models.TextField()

    total_marks = models.IntegerField(default=100)

    due_date = models.DateField()

    # 🔥 FILE ATTACHMENT (IMPORTANT FOR DOWNLOAD/VIEW)
    attachment = models.FileField(
        upload_to="assignments/",
        null=True,
        blank=True
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


# =========================
# SUBMISSION MODEL
# =========================
class Submission(models.Model):

    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("graded", "Graded"),
    ]

    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE
    )

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="submissions"
    )

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE
    )

    # 🔥 STUDENT UPLOADED FILE
    file = models.FileField(
        upload_to="assignments/submissions/"
    )

    submitted_at = models.DateTimeField(auto_now_add=True)

    # grading
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    feedback = models.TextField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="submitted"
    )

    def __str__(self):
        return f"{self.student.name} - {self.assignment.title}"