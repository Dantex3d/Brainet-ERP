# schools/middleware.py

from django.shortcuts import redirect
from django.contrib.auth import logout
from django.urls import resolve, Resolver404


class SchoolActivationMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.user.is_authenticated:

            school = getattr(request.user, "school", None)

            if school and not school.is_active:

                # Allow certain named routes to proceed (avoid redirect loops)
                allowed_names = {
                    "school_deactivated",
                    "request_license_renewal",
                    "request_renewal",
                    "contact_admin",
                    "logout",
                    "login",
                }

                try:
                    match = resolve(request.path_info)
                    if match and match.url_name in allowed_names:
                        return self.get_response(request)
                except Resolver404:
                    # If path doesn't resolve, continue with fallback checks
                    pass

                # If user is DOS or Principal, redirect to deactivation/renewal page so they can request activation
                try:
                    is_dos = hasattr(request.user, 'dos_profile') or getattr(request.user, 'role', None) == 'dos'
                    is_principal = hasattr(request.user, 'principal') or getattr(request.user, 'role', None) == 'principal'
                except Exception:
                    is_dos = False
                    is_principal = False

                if is_dos or is_principal:
                    return redirect('school_deactivated', school_id=school.id)

                # Other users: show contact admin page
                return redirect('contact_admin')

        return self.get_response(request)