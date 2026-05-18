# billing/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from .models import Subscription, BillingLog

@receiver(post_save, sender=Subscription)
def notify_subscription(sender, instance, created, **kwargs):
    """
    Signal to send notification and create audit log
    whenever a subscription is created or updated.
    """
    if created:
        # Step 1: Create BillingLog entry
        BillingLog.objects.create(
            subscription=instance,
            status='processing'
        )

        # Step 2: Send email notification to DOS
        subject = f"Subscription Renewal - {instance.school.name}"
        message = (
            f"{instance.school.name} renewed for {instance.duration}.\n"
            f"Days remaining: {instance.days_remaining()}.\n"
            f"Amount: {instance.amount}."
        )
        send_mail(
            subject,
            message,
            'noreply@brainet.com',
            [instance.dos.email],
            fail_silently=True
        )

        # Step 3: Update BillingLog to delivered
        BillingLog.objects.filter(subscription=instance).update(status='delivered')

    else:
        # If subscription updated (e.g., extended or deactivated)
        BillingLog.objects.create(
            subscription=instance,
            status='success'
        )
