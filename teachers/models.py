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


class OnlineClass(models.Model):
    STATUS_CHOICES = [
        ("upcoming", "Upcoming"),
        ("live", "Live"),
        ("finished", "Finished"),
    ]

    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE
    )

    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE
    )

    subject = models.ForeignKey(
        "subjects.Subject",
        on_delete=models.CASCADE,
        null=True,
        blank=True
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

    topic = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)

    meeting_link = models.URLField(blank=True, null=True)
    tools = models.CharField(max_length=250, blank=True, default="Screen Share, Chat, Whiteboard")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="upcoming"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_time"]

    def __str__(self):
        return f"{self.topic} — {self.class_obj.name}"

    @property
    def current_status(self):
        from django.utils import timezone

        now = timezone.now()

        if self.start_time <= now <= self.end_time:
            return "live"
        if now < self.start_time:
            return "upcoming"
        return "finished"

    @property
    def tool_list(self):
        return [tool.strip() for tool in self.tools.split(",") if tool.strip()]


class OnlineClassParticipant(models.Model):
    STATUS_CHOICES = [
        ("not_tried", "Not Tried"),
        ("joined", "Joined"),
        ("failed", "Failed to Join"),
    ]

    online_class = models.ForeignKey(
        OnlineClass,
        on_delete=models.CASCADE,
        related_name="participants"
    )

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="not_tried"
    )

    mic_enabled = models.BooleanField(default=False)
    joined_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("online_class", "student")

    def __str__(self):
        return f"{self.student.name} - {self.online_class.topic}"
