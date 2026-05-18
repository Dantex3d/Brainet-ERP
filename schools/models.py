import uuid
from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from django.utils import timezone


# =========================================================
# PHONE VALIDATOR
# =========================================================

phone_regex = RegexValidator(
    regex=r'^\+?\d{9,15}$',
    message="Phone number must be in format like +254712345678"
)


# =========================================================
# SCHOOL
# =========================================================
class Teacher(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=17, validators=[phone_regex], unique=True)

    def __str__(self):
        return self.name    
    
class School(models.Model):
    name = models.CharField(max_length=200, unique=True)
    address = models.TextField()

    phone = models.CharField(max_length=17, validators=[phone_regex], unique=True)
    email = models.EmailField(unique=True)

    logo = models.ImageField(upload_to="school_logos/", null=True, blank=True)

    principal_name = models.CharField(max_length=200, blank=True, null=True)
    principal_contact = models.CharField(max_length=20, blank=True, null=True)

    subscription_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# =========================================================
# DOS
# =========================================================

class DirectorOfStudies(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dos_profile",
        null=True,
        blank=True
    )

    school = models.OneToOneField(School, on_delete=models.CASCADE, related_name="dos")

    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=17, validators=[phone_regex], unique=True)

    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.school.name}"


# =========================================================
# TERM
# =========================================================

class Term(models.Model):
    STATUS = (
        ("open", "Open"),
        ("closed", "Closed"),
    )

    school = models.ForeignKey(School, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)

    opening_date = models.DateField()
    closing_date = models.DateField()

    status = models.CharField(max_length=20, choices=STATUS, default="open")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.school.name}"


# =========================================================
# CLASS
# =========================================================

class Class(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True, null=True)

    level = models.PositiveIntegerField(default=1)

    is_active = models.BooleanField(default=True)

    teacher = models.ForeignKey(
        "teachers.Teacher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="class_teacher"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["level", "name"]
        unique_together = ("school", "name", "level")

    def __str__(self):
        return f"{self.name} - {self.school.name}"


# =========================================================
# SUBJECT
# =========================================================

class Subject(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.name


# =========================================================
# CLASS ↔ SUBJECT ASSIGNMENT (FINAL CLEAN VERSION)
# =========================================================

class ClassSubject(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)

    class_name = models.ForeignKey(Class, on_delete=models.CASCADE)
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


# =========================================================
# GRADING POLICY
# =========================================================

class GradingPolicy(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)

    grade_letter = models.CharField(max_length=5)
    short_form = models.CharField(max_length=5, blank=True, null=True)

    min_score = models.IntegerField()
    max_score = models.IntegerField()

    points = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    remarks = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-min_score"]

    def __str__(self):
        return f"{self.grade_letter} ({self.min_score}-{self.max_score})"


# =========================================================
# STUDENT MARKS (CORE ENGINE)
# =========================================================

class StudentMark(models.Model):
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE)
    class_subject = models.ForeignKey(ClassSubject, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)

    marks = models.DecimalField(max_digits=5, decimal_places=2)

    grade = models.CharField(max_length=5, blank=True)
    points = models.DecimalField(max_digits=4, decimal_places=1, default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student} - {self.class_subject}"


# =========================================================
# EXAM SETTINGS
# =========================================================

class ExamSettings(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)

    term = models.CharField(max_length=20)

    cat_weight = models.DecimalField(max_digits=5, decimal_places=2, default=20)
    midterm_weight = models.DecimalField(max_digits=5, decimal_places=2, default=30)
    final_weight = models.DecimalField(max_digits=5, decimal_places=2, default=50)

    updated_by = models.CharField(max_length=100)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.term} Settings"


# =========================================================
# DORMITORY
# =========================================================

class Dormitory(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)

    name = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField(default=0)

    supervisor = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.school.name})"


# =========================================================
# STREAM (OPTIONAL STRUCTURE)
# =========================================================

class Stream(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)

    class_name = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="streams")

    name = models.CharField(max_length=50)

    class_teacher = models.ForeignKey(
        "teachers.Teacher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stream_teacher"
    )

    def __str__(self):
        return f"{self.class_name.name} {self.name}"
class TeacherSubject(models.Model):
    teacher = models.ForeignKey(
        "teachers.Teacher",
        on_delete=models.CASCADE,
        related_name="teacher_subjects"
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("teacher", "subject")

    def __str__(self):
        return f"{self.teacher} - {self.subject}"  
    