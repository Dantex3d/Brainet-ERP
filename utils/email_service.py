from django.conf import settings
from django.core.mail import EmailMultiAlternatives


def send_email(to_email, subject, message, recipient_name=None, html=True):
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
      
