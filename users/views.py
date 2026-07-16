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
from schools.models import School
from utils.email_service import send_email
from .forms import CustomAuthenticationForm


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