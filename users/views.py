from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
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

from django.contrib import messages
from django.contrib.auth import get_user_model
from schools.models import School

User = get_user_model()


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