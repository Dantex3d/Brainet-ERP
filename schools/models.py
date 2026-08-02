import uuid

from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from django.utils import timezone
from django.contrib.auth import get_user_model
from users.models import CustomUser
from classes.models import Class
from subjects.models import Subject

try:
    from cloudinary.models import CloudinaryField
except ImportError:  # pragma: no cover - exercised when cloudinary is not installed
    class CloudinaryField(models.ImageField):
        def __init__(self, *args, **kwargs):
            kwargs.setdefault("upload_to", "uploads")
            super().__init__(*args, **kwargs)

User = get_user_model()

# =========================================================
# PHONE VALIDATOR
# ========================================================

# =========================================================
# SCHOOL
# =========================================================
from django.db import models
from users.models import CustomUser
from django.core.validators import RegexValidator
from django.db import models

phone_regex = RegexValidator(
    regex=r'^\+254[17]\d{8}$',
    message="Phone number must be in format +2547XXXXXXXX or +2541XXXXXXXX."
)


# =========================================================
# PHONE NORMALIZATION
# =========================================================

def normalize_kenya_phone(phone):
    if not phone:
        return None

    phone = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not phone:
        return None

    if phone.startswith("+254"):
        return phone

    if phone.startswith("254"):
        return "+" + phone

    if phone == "07":
        return "+2547"

    if phone == "01":
        return "+2541"

    if phone.startswith("0") and phone[1:2] in {"7", "1"}:
        return "+254" + phone[1:]

    if phone.startswith(("7", "1")):
        return "+254" + phone

    return phone

class School(models.Model):
    LICENSE_STATUS = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
    ]

    name = models.CharField(max_length=200, unique=True)
    address = models.TextField()
    motto = models.CharField(max_length=300, null=True, blank=True)

    phone = models.CharField(
    max_length=20,
    validators=[phone_regex],
    unique=True,
    null=True,
    blank=True
)
    email = models.EmailField(unique=True)

    logo = CloudinaryField('image', blank=True, null=True)

    subscription_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bank_name = models.CharField(max_length=250, blank=True, null=True)
    account_number = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_schools"
    )
    verification_token = models.CharField(max_length=64, blank=True, null=True, unique=True)
    verification_sent_at = models.DateTimeField(null=True, blank=True)
    verification_code = models.CharField(max_length=6, blank=True, null=True)
    verification_code_sent_at = models.DateTimeField(null=True, blank=True)
    county = models.CharField(max_length=100, blank=True, null=True)
    admin_name = models.CharField(max_length=200, blank=True, null=True)
    admin_email = models.EmailField(blank=True, null=True)
    admin_phone = models.CharField(max_length=20, blank=True, null=True)
    registration_status = models.CharField(
        max_length=20,
        choices=[('draft', 'Draft'), ('pending', 'Pending Approval'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='draft'
    )
    admin_account_created = models.BooleanField(default=False)

    # License management
    license_status = models.CharField(max_length=20, choices=LICENSE_STATUS, default='active')
    license_expiry = models.DateField(null=True, blank=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    deactivation_reason = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def generate_verification_token(self):
        import secrets

        token = secrets.token_urlsafe(32)
        self.verification_token = token
        self.verification_sent_at = timezone.now()
        self.save(update_fields=["verification_token", "verification_sent_at"])
        return token

    def generate_verification_code(self):
        import random

        code = f"{random.randint(0, 999999):06d}"
        self.verification_code = code
        self.verification_code_sent_at = timezone.now()
        self.save(update_fields=["verification_code", "verification_code_sent_at"])
        return code

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
    phone = models.CharField(
    max_length=20,
    validators=[phone_regex],
    unique=True,
    null=True,
    blank=True
)
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
    phone = models.CharField(
    max_length=20,
    validators=[phone_regex],
    unique=True,
    null=True,
    blank=True
)

    def __str__(self):
        return f"{self.name} ({self.school.name})"
 


# =========================================================
# TERM
# =========================================================


class SupportAgent(models.Model):
    """Represents a support team member who can assist with user requests and demo responses."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='support_agent_profile'
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        try:
            return self.user.get_full_name() or self.user.email
        except Exception:
            return str(self.user)


class Term(models.Model):
    school = models.ForeignKey("schools.School", on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
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

    grade_letter = models.CharField(max_length=100)
    short_form = models.CharField(max_length=5, blank=True, null=True)

    min_score = models.IntegerField()
    max_score = models.IntegerField()

    points = models.IntegerField(default=0)
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
    exam = models.ForeignKey(
        "exams.Exam",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    marks = models.DecimalField(max_digits=5, decimal_places=2)

    grade = models.CharField(max_length=100, blank=True)
    points = models.DecimalField(max_digits=4, decimal_places=1, default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        subject_name = self.subject.name if self.subject else "No Subject"
        exam_name = self.exam.name if self.exam else "No Exam"
        return f"{self.student} - {subject_name} ({self.term}) [{exam_name}]"


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


class SecurityLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="security_logs"
    )
    event_type = models.CharField(max_length=80)
    message = models.TextField(blank=True, default="")
    path = models.CharField(max_length=500, blank=True, null=True)
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    user_agent = models.TextField(blank=True, default="")
    browser = models.CharField(max_length=120, blank=True, default="")
    location = models.CharField(max_length=200, blank=True, default="")
    status_code = models.IntegerField(default=0)
    details = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} @ {self.created_at}" 


class ErrorReport(models.Model):
    school = models.ForeignKey(
        "School",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="error_reports"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="error_reports"
    )
    path = models.CharField(max_length=500, blank=True, null=True)
    method = models.CharField(max_length=10, blank=True, null=True)
    exception_type = models.CharField(max_length=255)
    message = models.TextField()
    traceback = models.TextField(blank=True, null=True)
    data = models.TextField(blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.exception_type} @ {self.path or 'unknown'}"


# =========================================================
# DEMO REQUESTS
# =========================================================

class DemoRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True, null=True)
    intended_school = models.CharField(max_length=255)
    position_rank = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_demo_requests"
    )
    review_note = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.full_name} - {self.intended_school}"


# =========================================================
# Contact submissions from landing page
# =========================================================

class ContactMessage(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True, null=True)
    message = models.TextField()
    browser_used = models.CharField(max_length=500, blank=True, null=True)
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    reply = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    replied_at = models.DateTimeField(blank=True, null=True)
    handled = models.BooleanField(default=False)

    def __str__(self):
        return f"Contact from {self.name} <{self.email}>"


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


# =========================================================
# SCHOOL NOTICE
# =========================================================

class SchoolNotice(models.Model):
    RECIPIENT_CHOICES = [
        ('teachers', 'Teachers Only'),
        ('students', 'Students Only'),
        ('all', 'Teachers & Students'),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='notices')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    title = models.CharField(max_length=300)
    message = models.TextField()
    
    recipient_type = models.CharField(max_length=20, choices=RECIPIENT_CHOICES, default='all')
    
    is_urgent = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Principal follow-up / moderation fields
    follow_up = models.TextField(null=True, blank=True)
    followed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='followed_notices'
    )
    followed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.school.name} - {self.title}"