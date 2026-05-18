from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy


# =========================================================
# LOGIN VIEW (ONLY LOGIN SYSTEM)
# =========================================================

class CustomLoginView(LoginView):
    template_name = 'users/login.html'
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

        elif role == 'class_teacher':
            return reverse_lazy('class_teacher_dashboard')

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

    user = request.user

    # SUPERUSER
    if user.is_superuser:
        return render(request, 'dashboards/superuser.html')

    role = getattr(user, 'role', None)

    if role == 'dos':
        return render(request, 'dashboards/dos.html')

    elif role == 'principal':
        return render(request, 'dashboards/principal.html')

    elif role == 'class_teacher':
        return render(request, 'dashboards/class_teacher.html')

    elif role == 'subject_teacher':
        return render(request, 'dashboards/subject_teacher.html')

    elif role == 'student':
        return render(request, 'dashboards/student.html')

    # SAFE FALLBACK
    return render(request, 'dashboards/landing.html')
def custom_logout(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect('home')

