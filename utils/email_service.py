import os

import sib_api_v3_sdk
from django.conf import settings
from django.core.mail import EmailMultiAlternatives


def send_email_with_brevo(to_email, subject, message, recipient_name=None, html=True):
    """Send transactional email via Brevo / SendinBlue API."""
    api_key = os.environ.get('BREVO_API_KEY') or os.environ.get('SENDINBLUE_API_KEY')
    if not api_key or not to_email:
        return False

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = api_key
    api_client = sib_api_v3_sdk.ApiClient(configuration)
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(api_client)

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'EMAIL_HOST_USER', None)
    if not from_email:
        return False

    sender_name = getattr(settings, 'SITE_NAME', 'Brainet')
    from_payload = {'email': from_email, 'name': sender_name}

    recipients = [to_email] if isinstance(to_email, str) else list(to_email)
    recipient_payload = [
        sib_api_v3_sdk.SendSmtpEmailTo(email=recipient, name=recipient_name or recipient)
        for recipient in recipients
    ]

    text_content = message.replace('<br>', '\n') if html and '<' in message else message

    email_payload = sib_api_v3_sdk.SendSmtpEmail(
        sender=sib_api_v3_sdk.SendSmtpEmailSender(email=from_email, name=sender_name),
        to=recipient_payload,
        subject=subject,
        html_content=message if html else None,
        text_content=text_content if html else message,
    )

    try:
        api_instance.send_transac_email(email_payload)
        return True
    except Exception as e:
        print('Brevo send error:', e)
        return False


def send_email(to_email, subject, message, recipient_name=None, html=True):
    """
    Send an email using Brevo API when configured, otherwise use Django's email backend.

    - `to_email`: recipient email address (string) or list
    - `subject`: email subject
    - `message`: plain text or HTML body
    - `recipient_name`: optional recipient display name to personalize headers
    - `html`: whether `message` contains HTML
    """
    if not to_email:
        return False

    if os.environ.get('BREVO_API_KEY') or os.environ.get('SENDINBLUE_API_KEY'):
        return send_email_with_brevo(to_email, subject, message, recipient_name=recipient_name, html=html)

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or getattr(settings, "EMAIL_HOST_USER", None)

    # Build a friendly "From" header
    from_header = f"{getattr(settings, 'SITE_NAME', 'Brainet')} <{from_email}>" if from_email else None
    if from_header:
        from_email = from_header

    # Ensure to_email is a list
    recipients = [to_email] if isinstance(to_email, str) else list(to_email)

    try:
        if html:
            text_content = message.replace("<br>", "\n") if "<" in message else message
            msg = EmailMultiAlternatives(subject, text_content, from_email, recipients)
            msg.attach_alternative(message, "text/html")
        else:
            msg = EmailMultiAlternatives(subject, message, from_email, recipients)

        # Optional: set a Reply-To to the site support email
        support = getattr(settings, 'SUPPORT_EMAIL', None) or from_email
        if support:
            msg.extra_headers = {'Reply-To': support}

        msg.send(fail_silently=False)
        return True
    except Exception as e:
        # Keep failures quiet but log for debugging during development
        try:
            print("Email send error:", str(e))
        except Exception:
            pass
        return False
    """
    Send an email using Django's configured email backend (SMTP/Zoho).

    - `to_email`: recipient email address (string) or list
    - `subject`: email subject
    - `message`: plain text or HTML body
    - `recipient_name`: optional recipient display name to personalize headers
    - `html`: whether `message` contains HTML
    """
    if not to_email:
        return False

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or getattr(settings, "EMAIL_HOST_USER", None)

    # Build a friendly "From" header
    from_header = f"{getattr(settings, 'SITE_NAME', 'Brainet')} <{from_email}>" if from_email else None
    if from_header:
        from_email = from_header

    # Ensure to_email is a list
    recipients = [to_email] if isinstance(to_email, str) else list(to_email)

    try:
        if html:
            text_content = message.replace("<br>", "\n") if "<" in message else message
            msg = EmailMultiAlternatives(subject, text_content, from_email, recipients)
            msg.attach_alternative(message, "text/html")
        else:
            msg = EmailMultiAlternatives(subject, message, from_email, recipients)

        # Optional: set a Reply-To to the site support email
        support = getattr(settings, 'SUPPORT_EMAIL', None) or from_email
        if support:
            msg.extra_headers = {'Reply-To': support}

        msg.send(fail_silently=False)
        return True
    except Exception as e:
        # Keep failures quiet but log for debugging during development
        try:
            print("Email send error:", str(e))
        except Exception:
            pass
        return False
      
