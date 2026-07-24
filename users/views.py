import json
import secrets
import urllib.request
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, update_session_auth_hash, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.mail import get_connection
from django.urls import reverse, reverse_lazy
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from schools.models import School, SecurityLog
from utils.email_service import send_email
from .forms import CustomAuthenticationForm
from utils.ip_utils import (
    get_client_ip,
    get_browser_name,
    resolve_location,
)


def _get_trusted_device_key(user, request):
    ip_address = get_client_ip(request)
    browser = get_browser_name(request.META.get("HTTP_USER_AGENT", ""))
    return f"trusted_device_{user.pk}_{ip_address}_{browser}"


def _is_superuser_trusted_device_feature_enabled():
    return getattr(settings, 'SUPERUSER_TRUSTED_DEVICE_ENABLED', True)


def _is_trusted_device(user, request):
    if not _is_superuser_trusted_device_feature_enabled():
        return False
    return bool(request.session.get(_get_trusted_device_key(user, request)))


def _trust_device(user, request):
    if not _is_superuser_trusted_device_feature_enabled():
        return
    request.session[_get_trusted_device_key(user, request)] = True
    request.session.modified = True

def _record_security_event(request, user=None, event_type="", message="", status_code=0, details=None):
    ip_address = get_client_ip(request)
    browser = get_browser_name(request.META.get("HTTP_USER_AGENT", ""))
    location = resolve_location(ip_address)
    return SecurityLog.objects.create(
        user=user,
        event_type=event_type,
        message=message,
        path=getattr(request, "path", None),
        ip_address=ip_address,
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        browser=browser,
        location=location,
        status_code=status_code,
        details=json.dumps(details or {}, default=str),
    )


def _send_login_security_email(user, event_type, details):
    if not user or not getattr(user, "email", None):
        return

    subject = "Security warning: unusual login activity on your Brainet account"
    ip_address = details.get("ip_address") or "Unknown"
    browser = details.get("browser") or "Unknown"
    location = details.get("location") or "Unknown"
    message = (
        f"Hello {user.get_full_name() or user.email},\n\n"
        f"We detected {event_type.replace('_', ' ')} for your Brainet account.\n\n"
        f"Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"IP address: {ip_address}\n"
        f"Browser: {browser}\n"
        f"Location: {location}\n\n"
        "If this was not you, please change your password immediately and contact support."
    )
    send_email(
        to_email=user.email,
        subject=subject,
        message=message,
        recipient_name=user.get_full_name() or user.email,
        html=False,
    )


# =========================================================
# LOGIN VIEW (ONLY LOGIN SYSTEM)
# =========================================================

class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    authentication_form = CustomAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        """Override form_valid to check verification status"""
        user = form.get_user()
        remember_me = bool(form.cleaned_data.get("remember_me"))
        trust_device = bool(form.cleaned_data.get("trust_device"))

        if user.is_superuser:
            if _is_trusted_device(user, self.request):
                login(self.request, user)
                if remember_me:
                    self.request.session.set_expiry(settings.SESSION_COOKIE_AGE)
                else:
                    self.request.session.set_expiry(0)
                return redirect(self.get_success_url())

            self.request.session["pending_superuser_login_user_id"] = user.pk
            self.request.session["pending_superuser_login_remember_me"] = remember_me
            self.request.session["pending_superuser_login_trust_device"] = trust_device
            self._start_superuser_two_factor(user)
            return redirect('superuser_two_factor')

        # For DOS/Principal/Teacher, require email verification before allowing login
        if user.role in ['dos', 'principal', 'teacher'] and not user.email_verified:
            role_map = {'dos': 'DOS', 'principal': 'Principal', 'teacher': 'Teacher'}
            role_name = role_map.get(user.role, user.role)
            messages.warning(
                self.request,
                f"Your {role_name} account requires verification. Please check your email for the verification code."
            )
            return redirect(f"{reverse('verify_user_code')}?email={user.email}")

        # Normal login flow
        login(self.request, user)

        remember_me = form.cleaned_data.get("remember_me")
        if remember_me:
            self.request.session.set_expiry(settings.SESSION_COOKIE_AGE)
        else:
            self.request.session.set_expiry(0)

        return redirect(self.get_success_url())

    def form_invalid(self, form):
        email = (self.request.POST.get("username") or "").strip()
        user = None
        if email:
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                user = None
        details = {"username": email}
        self._record_security_log(
            event_type="login_failed",
            message="Invalid login attempt",
            user=user,
            status_code=400,
            details=details,
        )
        return super().form_invalid(form)

    def _start_superuser_two_factor(self, user):
        code = f"{secrets.randbelow(900000) + 100000}"
        self.request.session["pending_superuser_login_user_id"] = user.pk
        self.request.session["pending_superuser_login_code"] = code
        self.request.session["pending_superuser_login_attempts"] = 0
        self.request.session.set_expiry(300)

        message = (
            f"Your Brainet security code is {code}. "
            "Enter it to continue to the superuser dashboard."
        )
        try:
            email_sent = send_email(
                to_email=user.email,
                subject="Brainet superuser verification code",
                message=message,
                recipient_name=user.get_full_name() or user.email,
                html=False,
            )
        except Exception:
            email_sent = False

        if email_sent:
            status_message = "Superuser verification code sent"
        else:
            status_message = "Superuser verification code prepared locally; email delivery failed"

        self._record_security_log(
            event_type="superuser_login_requested",
            message=status_message,
            user=user,
            status_code=302,
            details={"email": user.email},
        )

    def _record_security_log(self, event_type, message, user=None, status_code=0, details=None):
        try:
            log_record = _record_security_event(
                self.request,
                user=user,
                event_type=event_type,
                message=message,
                status_code=status_code,
                details=details,
            )
            if event_type in {"login_failed", "superuser_two_factor_failed", "superuser_two_factor_locked"} and user:
                _send_login_security_email(user, event_type, {
                    "ip_address": log_record.ip_address,
                    "browser": log_record.browser,
                    "location": log_record.location,
                })
        except Exception:
            pass

    def _get_client_ip(self):
        return get_client_ip(self.request)

    def get_success_url(self):

        user = self.request.user

        # SUPERUSER → Django-like admin dashboard
        if user.is_superuser:
            return reverse_lazy('superuser_dashboard')

        # ROLE-BASED REDIRECTS
        role = getattr(user, 'role', None)

        if role == 'dos':
            return reverse_lazy('dos_dashboard')

        elif role == 'principal':
            return reverse_lazy('principal_dashboard')

        elif role == 'teacher':
            return reverse_lazy('teacher_dashboard')

        elif role == 'subject_teacher':
            return reverse_lazy('subject_teacher_dashboard')

        elif role == 'bursar':
            return reverse_lazy('fees_dashboard')

        elif role == 'student':
            return reverse_lazy('student_dashboard')

        # fallback
        return reverse_lazy('dashboard')


# =========================================================
# ROLE DASHBOARD ROUTER (SAFE DISPLAY VIEW)
# =========================================================

@login_required
def dashboard(request):
    # Redirect to the richer role-specific dashboard views which prepare data
    user = request.user

    if user.is_superuser:
        return redirect('superuser_dashboard')

    role = getattr(user, 'role', None)

    if role == 'dos':
        return redirect('dos_dashboard')

    elif role == 'principal':
        return redirect('principal_dashboard')

    elif role == 'class_teacher':
        return redirect('principal_dashboard')

    elif role == 'teacher':
        return redirect('teacher_dashboard')

    elif role == 'subject_teacher':
        return redirect('teacher_dashboard')

    elif role == 'bursar':
        return redirect('fees_dashboard')

    elif role == 'student':
        return redirect('student_dashboard')

    # SAFE FALLBACK
    return render(request, 'dashboards/landing.html')
def custom_logout(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect('home')


@csrf_protect
def superuser_two_factor(request):
    if request.method == "POST":
        code = (request.POST.get("code") or "").strip()
        expected_code = request.session.get("pending_superuser_login_code")
        user_id = request.session.get("pending_superuser_login_user_id")

        if not expected_code or not user_id:
            messages.error(request, "Your verification session has expired. Please log in again.")
            return redirect('login')

        attempts = int(request.session.get("pending_superuser_login_attempts", 0)) + 1
        request.session["pending_superuser_login_attempts"] = attempts
        request.session.modified = True

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            messages.error(request, "Your verification session is invalid. Please log in again.")
            return redirect('login')

        if code != expected_code:
            if attempts >= 3:
                request.session.pop("pending_superuser_login_code", None)
                request.session.pop("pending_superuser_login_user_id", None)
                request.session.pop("pending_superuser_login_attempts", None)
                _record_security_event(
                    request,
                    user=user,
                    event_type="superuser_two_factor_locked",
                    message="Superuser 2FA attempts exceeded",
                    status_code=400,
                )
                messages.error(request, "Too many failed verification attempts. Please log in again.")
                return redirect('login')

            _record_security_event(
                request,
                user=user,
                event_type="superuser_two_factor_failed",
                message="Incorrect 2FA code",
                status_code=400,
            )
            messages.error(request, "The verification code is incorrect. Please try again.")
            return render(request, "users/superuser_two_factor.html")

        pending_remember_me = bool(request.session.pop("pending_superuser_login_remember_me", False))
        pending_trust_device = bool(request.session.pop("pending_superuser_login_trust_device", False))
        request.session.pop("pending_superuser_login_code", None)
        request.session.pop("pending_superuser_login_user_id", None)
        request.session.pop("pending_superuser_login_attempts", None)

        trust_device = request.POST.get("trust_device") == "on" or pending_trust_device
        if trust_device:
            _trust_device(user, request)

        login(request, user)
        if pending_remember_me or trust_device:
            request.session.set_expiry(settings.SESSION_COOKIE_AGE)
        else:
            request.session.set_expiry(0)

        _record_security_event(
            request,
            user=user,
            event_type="superuser_login_completed",
            message="Superuser verified and logged in",
            status_code=200,
        )
        return redirect('superuser_dashboard')

    return render(request, 'users/superuser_two_factor.html')

@login_required
def account_profile(request):
    user = request.user
    profile = None
    profile_type = None
    profile_name = None
    profile_school = None
    profile_email = user.email

    if hasattr(user, 'teacher'):
        profile = user.teacher
        profile_type = 'Teacher'
        profile_name = profile.name
        profile_school = getattr(profile.school, 'name', None)
    elif hasattr(user, 'dos_profile'):
        profile = user.dos_profile
        profile_type = 'Director of Studies'
        profile_name = profile.name
        profile_email = profile.email
        profile_school = getattr(profile.school, 'name', None)
    elif hasattr(user, 'principal'):
        profile = user.principal
        profile_type = 'Principal'
        profile_name = profile.name
        profile_email = profile.email
        profile_school = getattr(profile.school, 'name', None)
    elif hasattr(user, 'student_profile'):
        profile = user.student_profile
        profile_type = 'Student'
        profile_name = profile.name
        profile_school = getattr(profile.school, 'name', None)
    else:
        profile_type = 'User'
        profile_school = getattr(user.school, 'name', None)

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        name = request.POST.get('name', '').strip()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if email and email != user.email:
            if User.objects.filter(email=email).exclude(pk=user.pk).exists():
                messages.error(request, 'Email address is already in use.')
                return redirect('account_profile')
            user.email = email
            if profile and hasattr(profile, 'email'):
                profile.email = email

        if profile and name:
            if hasattr(profile, 'name'):
                profile.name = name

        if password:
            if password != confirm_password:
                messages.error(request, 'Passwords do not match.')
                return redirect('account_profile')
            user.set_password(password)
            update_session_auth_hash(request, user)

        user.save()
        if profile:
            profile.save()

        messages.success(request, 'Account details updated successfully.')
        return redirect('account_profile')

    return render(request, 'users/account_profile.html', {
        'user': user,
        'profile_type': profile_type,
        'profile_name': profile_name,
        'profile_school': profile_school,
        'profile_email': profile_email,
    })

User = get_user_model()


def _verification_contact_message(request=None):
    try:
        from django.urls import reverse
        contact_path = reverse('contact_admin')
    except Exception:
        contact_path = getattr(settings, 'CONTACT_ADMIN_PATH', '/schools/contact-admin/')

    support_email = getattr(settings, 'SUPPORT_EMAIL', 'merkoudaniel@gmail.com')
    whatsapp_1 = getattr(settings, 'SUPPORT_WHATSAPP_1', '0700269517')
    whatsapp_2 = getattr(settings, 'SUPPORT_WHATSAPP_2', '0736645038')
    absolute_contact = request.build_absolute_uri(contact_path) if request else contact_path

    return (
        f"Contact Brainet support or your administrator: {absolute_contact} | "
        f"WhatsApp/SMS: {whatsapp_1}, {whatsapp_2} | Email: {support_email}"
    )


def send_verification_email(user, request=None):
    if not user.email:
        return False

    token = user.generate_email_verification_token()
    verify_link = None
    if request:
        verify_link = request.build_absolute_uri(reverse('verify_user_email', args=[token]))
    else:
        verify_link = reverse('verify_user_email', args=[token])

    subject = 'Verify your Brainet account'
    body = (
        f"Hello {getattr(user, 'first_name', user.email)},\n\n"
        f"Please verify your email address by clicking the link below:\n\n{verify_link}\n\n"
        "This link expires in 1 hour. If it expires, request a new verification email.\n\n"
        "If you did not request this, please ignore this message."
    )

    return send_email(
        to_email=user.email,
        subject=subject,
        message=body,
        recipient_name=getattr(user, 'first_name', user.email),
        html=False,
    )


def verify_user_email(request, token):
    user = get_object_or_404(User, email_verification_token=token)

    if not user.email_verification_sent_at or user.email_verification_sent_at + timedelta(hours=1) < timezone.now():
        user.email_verification_token = None
        user.save(update_fields=["email_verification_token"])
        messages.error(request, 'Verification link has expired. Please request a new verification email.')
        return redirect('home')

    user.mark_email_verified()
    messages.success(request, 'Your email has been verified successfully. Please log in.')
    return redirect('home')


def verify_user_code(request):
    """Verify user account using a numeric verification code (for DOS/Principal/Teacher)"""
    email = request.GET.get('email') or request.POST.get('email')
    
    if not email:
        messages.error(request, 'Email address is required.')
        return redirect('home')
    
    try:
        user = User.objects.get(email=email, role__in=['dos', 'principal', 'teacher'])
    except User.DoesNotExist:
        messages.error(request, 'Account not found or verification not required.')
        return redirect('home')
    
    if user.email_verified:
        messages.info(request, 'Your account is already verified. Please log in.')
        return redirect('home')
    
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        success, message = user.verify_code(code)
        
        if success:
            messages.success(request, message + ' You can now log in.')
            return redirect('home')
        else:
            messages.error(request, message)
            return render(request, 'users/verify_code.html', {'email': email})
    
    return render(request, 'users/verify_code.html', {'email': email})


def resend_verification_code(request):
    """Resend verification code for DOS/Principal/Teacher accounts"""
    email = request.GET.get('email') or request.POST.get('email')
    
    if not email:
        messages.error(request, 'Email address is required.')
        return redirect('home')
    
    try:
        user = User.objects.get(email=email, role__in=['dos', 'principal', 'teacher'])
    except User.DoesNotExist:
        messages.error(request, 'Account not found.')
        return redirect('home')
    
    if user.email_verified:
        messages.info(request, 'Your account is already verified.')
        return redirect('home')
    
    # Regenerate and send code
    from schools.views import send_user_verification_email
    try:
        if send_user_verification_email(user, request=request, role_name=user.get_role_display()):
            messages.success(request, 'A new verification code has been sent to your email.')
        else:
            messages.error(request, f'The verification email could not be sent right now. {_verification_contact_message(request)}')
    except Exception as e:
        messages.error(request, f'Failed to send verification email: {str(e)}')
    return redirect(f"{reverse('verify_user_code')}?email={email}")


@login_required
def resend_verification_email(request):
    user = request.user
    if user.email_verified:
        messages.info(request, 'Your account is already verified.')
        return redirect('account_profile')

    try:
        if send_verification_email(user, request=request):
            messages.success(request, 'Verification email sent. Check your inbox.')
        else:
            messages.error(request, f'Verification email could not be sent right now. {_verification_contact_message(request)}')
    except Exception as e:
        messages.error(request, f'Failed to send verification email: {str(e)}')
    return redirect('account_profile')


def create_custom_user(request):
    if request.method == "POST":

        email = request.POST.get("email")
        password = request.POST.get("password")
        role = request.POST.get("role")
        school_id = request.POST.get("school")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already taken")
            return redirect("superuser_dashboard")

        school = None
        if school_id:
            school = School.objects.get(id=school_id)

        user = User.objects.create_user(
            email=email,
            password=password,
            role=role,
            school=school
        )

        messages.success(request, f"{role} account created successfully")

        return redirect("superuser_dashboard")