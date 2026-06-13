from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, update_session_auth_hash, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.urls import reverse, reverse_lazy
from django.conf import settings
from django.utils import timezone
from schools.models import School
from .forms import CustomAuthenticationForm


# =========================================================
# LOGIN VIEW (ONLY LOGIN SYSTEM)
# =========================================================

class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    authentication_form = CustomAuthenticationForm
    redirect_authenticated_user = True

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


def send_verification_email(user, request=None):
    if not settings.EMAIL_HOST_USER or not user.email:
        return

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

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
    except Exception:
        pass


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