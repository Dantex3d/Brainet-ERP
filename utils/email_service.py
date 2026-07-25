import os
import traceback

try:
    import sib_api_v3_sdk
    from sib_api_v3_sdk.rest import ApiException
except ImportError:  # pragma: no cover - runtime fallback for environments without the SDK
    sib_api_v3_sdk = None
    ApiException = Exception
from django.conf import settings
from django.core.mail import EmailMultiAlternatives


def _get_api_key():
    return os.environ.get('BREVO_API_KEY') or os.environ.get('SENDINBLUE_API_KEY')


def _get_from_email():
    return (
        os.environ.get('BREVO_FROM_EMAIL')
        or getattr(settings, 'BREVO_FROM_EMAIL', None)
        or getattr(settings, 'DEFAULT_FROM_EMAIL', None)
        or getattr(settings, 'EMAIL_HOST_USER', None)
    )


def _format_recipients(to_email):
    return [to_email] if isinstance(to_email, str) else list(to_email)


def _log_exception(context, exception):
    print(f"{context} error type: {type(exception).__name__}")
    print(f"{context} error: {repr(exception)}")
    traceback.print_exc()

    for attr in ('body', 'status', 'headers'):
        if hasattr(exception, attr):
            print(f"{context} {attr}:", getattr(exception, attr))


def _extract_api_exception_message(exception):
    if isinstance(exception, ApiException):
        parts = []
        status = getattr(exception, 'status', None)
        body = getattr(exception, 'body', None)
        reason = getattr(exception, 'reason', None)
        if status is not None:
            parts.append(f'Status {status}')
        if reason:
            parts.append(reason)
        if body is not None:
            if isinstance(body, (bytes, bytearray)):
                try:
                    body = body.decode('utf-8')
                except Exception:
                    body = repr(body)
            try:
                import json
                parsed = json.loads(body)
                if isinstance(parsed, dict):
                    message_text = parsed.get('message') or parsed.get('error') or parsed.get('detail')
                    code_text = parsed.get('code')
                    if code_text == 'unauthorized' and message_text and 'Key not found' in message_text:
                        return 'Brevo API key invalid or not found. Check BREVO_API_KEY.'
                    if message_text:
                        parts.append(message_text)
                    elif code_text:
                        parts.append(code_text)
                    else:
                        parts.append(f'Body: {body}')
                else:
                    parts.append(f'Body: {body}')
            except Exception:
                parts.append(f'Body: {body}')
        if parts:
            return '; '.join(parts)
    text = str(exception)
    return text if text else repr(exception)


def send_email_with_brevo(to_email, subject, message, recipient_name=None, html=True):
    """Send transactional email via Brevo / SendinBlue API."""
    if sib_api_v3_sdk is None:
        raise RuntimeError('sib_api_v3_sdk is not installed')

    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError('Email service is not configured properly. Set BREVO_API_KEY or SENDINBLUE_API_KEY.')

    if not to_email:
        raise RuntimeError('Missing recipient email address')

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = api_key
    api_client = sib_api_v3_sdk.ApiClient(configuration)
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(api_client)

    from_email = _get_from_email()
    if not from_email:
        raise RuntimeError('Email service is not configured properly. Set DEFAULT_FROM_EMAIL or BREVO_FROM_EMAIL.')

    sender_name = getattr(settings, 'SITE_NAME', 'Brainet')
    recipients = _format_recipients(to_email)
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
        print('Brevo sender:', from_email)
        print('Brevo recipients:', recipients)
        print('Brevo subject:', subject)
        print('Brevo API key present:', bool(api_key))

        response = api_instance.send_transac_email(email_payload)
        print('Brevo success response:', response)
        return True
    except Exception as e:
        error_message = _extract_api_exception_message(e)
        _log_exception('Brevo send', e)
        raise RuntimeError(f'Brevo send failed: {error_message}')


def send_email_with_django(to_email, subject, message, recipient_name=None, html=True):
    """Send email via the Django email backend."""
    if not to_email:
        raise RuntimeError('Missing recipient email address')

    from_email = _get_from_email()
    if not from_email:
        raise RuntimeError('Email service is not configured properly. Set DEFAULT_FROM_EMAIL or BREVO_FROM_EMAIL.')

    sender_name = getattr(settings, 'SITE_NAME', 'Brainet')
    from_header = f"{sender_name} <{from_email}>" if from_email else from_email
    if from_header:
        from_email = from_header

    recipients = _format_recipients(to_email)
    text_content = message.replace('<br>', '\n') if html and '<' in message else message

    try:
        if html:
            msg = EmailMultiAlternatives(subject, text_content, from_email, recipients)
            msg.attach_alternative(message, 'text/html')
        else:
            msg = EmailMultiAlternatives(subject, message, from_email, recipients)

        support = getattr(settings, 'SUPPORT_EMAIL', None) or from_email
        if support:
            msg.extra_headers = {'Reply-To': support}

        msg.send(fail_silently=False)
        return True
    except Exception as e:
        _log_exception('Django email send', e)
        if settings.DEBUG:
            raise
        return False


def send_email(to_email, subject, message, recipient_name=None, html=True):
    """Send email using Brevo when configured, otherwise fall back to Django."""
    email_backend = getattr(settings, 'EMAIL_BACKEND', '') or ''
    if email_backend.endswith('locmem.EmailBackend'):
        return send_email_with_django(to_email, subject, message, recipient_name=recipient_name, html=html)

    api_key = _get_api_key()
    if api_key:
        try:
            return send_email_with_brevo(to_email, subject, message, recipient_name=recipient_name, html=html)
        except Exception as exc:
            if getattr(settings, 'EMAIL_HOST_USER', None) or getattr(settings, 'EMAIL_HOST_PASSWORD', None):
                try:
                    return send_email_with_django(to_email, subject, message, recipient_name=recipient_name, html=html)
                except Exception as django_exc:
                    raise RuntimeError(f'Email service failed through Brevo and SMTP fallback: {exc}; {django_exc}') from exc
            raise RuntimeError(f'Email service is not configured properly: {exc}') from exc

    return send_email_with_django(to_email, subject, message, recipient_name=recipient_name, html=html)
      