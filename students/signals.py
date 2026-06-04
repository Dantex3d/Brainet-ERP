"""
Signals for student-related actions (e.g., marking assignments, generating reports)
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from assignments.models import Submission
from schools.models import Notification


@receiver(post_save, sender=Submission)
def submission_marked_signal(sender, instance, created, **kwargs):
    """
    When a submission is marked (status='graded'), create a notification for the student
    and optionally trigger a report generation/email.
    """
    
    # Only process if status is 'graded' (not on creation)
    if instance.status == "graded":
        
        student = instance.student
        assignment = instance.assignment
        school = instance.school
        
        # Create notification for student about the grade
        Notification.objects.create(
            school=school,
            recipient=student.user,
            title="Assignment Graded",
            message=(
                f"Your assignment '{assignment.title}' has been graded. "
                f"Score: {instance.score}/{assignment.total_marks}"
            )
        )
        
        # Optional: Send email notification
        try:
            subject = f"Assignment Graded: {assignment.title}"
            message = (
                f"Dear {student.name},\n\n"
                f"Your assignment '{assignment.title}' has been graded.\n\n"
                f"Score: {instance.score}/{assignment.total_marks}\n"
                f"Feedback: {instance.feedback or 'No feedback provided'}\n\n"
                f"Please log in to view more details.\n\n"
                f"Best regards,\n{school.name}"
            )
            send_mail(
                subject,
                message,
                'no-reply@brainet.com',
                [student.user.email],
                fail_silently=True
            )
        except Exception as e:
            print(f"Error sending email: {str(e)}")
