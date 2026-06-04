import uuid
from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from django.utils import timezone
from django.contrib.auth import get_user_model
from users.models import CustomUser
from classes.models import Class
from subjects.models import Subject

User = get_user_model()

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
from django.db import models
from users.models import CustomUser
from django.core.validators import RegexValidator
from django.db import models

# Kenyan phone validator
phone_regex = RegexValidator(
    regex=r'^(?:07\d{8}|011\d{7}|\+254[17]\d{7})$',
    message="Phone number must be either 07xxxxxxxx (10 digits), 011xxxxxxx (10 digits), or +2547xxxxxxx / +2541xxxxxxx (13 digits)."
)

class School(models.Model):
    LICENSE_STATUS = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
    ]

    name = models.CharField(max_length=200, unique=True)
    address = models.TextField()

    phone = models.CharField(max_length=17, validators=[phone_regex], unique=True)
    email = models.EmailField(unique=True)

    logo = models.ImageField(upload_to="school_logos/", null=True, blank=True)

    subscription_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    
    # License management
    license_status = models.CharField(max_length=20, choices=LICENSE_STATUS, default='active')
    license_expiry = models.DateField(null=True, blank=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    deactivation_reason = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
    @property
    def is_license_active(self):
        """Check if license is still valid"""
        if self.license_status != 'active':
            return False
        if self.license_expiry:
            from django.utils import timezone
            return self.license_expiry >= timezone.now().date()
        return True



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
    
from django.db import models
from users.models import CustomUser

class Principal(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    school = models.ForeignKey("schools.School", on_delete=models.CASCADE, related_name="principals")
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.name} ({self.school.name})"
 


# =========================================================
# TERM
# =========================================================

class Term(models.Model):
    school = models.ForeignKey("schools.School", on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        # remove 'level' if it doesn't exist
        unique_together = ("school", "name", "start_date")
        ordering = ["start_date"]

    def __str__(self):
        return self.name


# =========================================================
# CLASS ↔ SUBJECT ASSIGNMENT (FINAL CLEAN VERSION)
# =========================================================



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
    subject = models.ForeignKey(
    Subject,
    on_delete=models.CASCADE,
    null=True,
    blank=True
)
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


from django.conf import settings
from django.db import models


from django.db import models
from schools.models import School
from users.models import CustomUser


class DOSQuery(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("replied", "Replied"),
        ("resolved", "Resolved"),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE)
    dos = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    subject = models.CharField(max_length=255)
    message = models.TextField()

    reply = models.TextField(blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    replied_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.school.name} - {self.subject}" 
    
class VoucherRequest(models.Model):
    
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE)
    term = models.CharField(max_length=100)
    student_count = models.IntegerField(default=0)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    created_at = models.DateTimeField(auto_now_add=True)   
class DOSMessage(models.Model):
    school = models.ForeignKey("School", on_delete=models.CASCADE)
    sender = models.ForeignKey("users.CustomUser", on_delete=models.CASCADE, related_name="sent_messages")
    receiver = models.ForeignKey("users.CustomUser", on_delete=models.CASCADE, related_name="received_messages")

    subject = models.CharField(max_length=255)
    message = models.TextField()

    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE)

    status = models.CharField(
        max_length=20,
        default="unread"
    )

    created_at = models.DateTimeField(auto_now_add=True)  
# schools/models.py (or notifications app later)

from django.conf import settings

class Notification(models.Model):

    school = models.ForeignKey(
        "School",
        on_delete=models.CASCADE
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_notifications"
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_notifications"
    )

    title = models.CharField(max_length=200)

    message = models.TextField()

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title      


# =========================================================
# STUDENT PROMOTION
# =========================================================

class StudentPromotion(models.Model):
    PROMOTION_STATUS = [
        ('promoted', 'Promoted'),
        ('repeated', 'Repeated'),
        ('graduated', 'Graduated'),
        ('dropped', 'Dropped'),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='promotions')
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='promotions')
    
    from_class = models.ForeignKey(
        'classes.Class',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students_promoted_from'
    )
    
    to_class = models.ForeignKey(
        'classes.Class',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students_promoted_to'
    )
    
    from_stream = models.ForeignKey(
        'classes.Stream',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students_promoted_from_stream'
    )
    
    to_stream = models.ForeignKey(
        'classes.Stream',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students_promoted_to_stream'
    )
    
    status = models.CharField(max_length=20, choices=PROMOTION_STATUS, default='promoted')
    remarks = models.TextField(null=True, blank=True)
    
    promoted_at = models.DateTimeField(auto_now_add=True)
    promoted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-promoted_at']

    def __str__(self):
        return f"{self.student.name} - {self.from_class} → {self.to_class}"


# =========================================================
# LICENSE RENEWAL
# =========================================================

class LicenseRenewal(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='license_renewals')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    requested_at = models.DateTimeField(auto_now_add=True)
    renewal_period_days = models.IntegerField(default=365, help_text="Number of days to extend the license")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_renewals'
    )
    
    notes = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f"{self.school.name} - Renewal Request ({self.status})"