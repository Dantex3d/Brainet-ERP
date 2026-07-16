# schools/middleware.py

import json
import logging
import traceback
from django.shortcuts import redirect, render
from django.contrib.auth import logout
from django.urls import resolve, Resolver404
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import Http404
from django.conf import settings
from .models import ErrorReport

logger = logging.getLogger(__name__)


class ErrorReporterMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except Http404 as exc:
            return render(request, "exams/errors/404.html", {"message": str(exc)}, status=404)
        except PermissionDenied:
            raise
        except SuspiciousOperation as exc:
            return render(request, "exams/errors/400.html", {"message": str(exc)}, status=400)
        except Exception as exc:
            traceback_data = traceback.format_exception(type(exc), exc, exc.__traceback__)
            report_data = {
                "GET": request.GET.dict(),
                "POST": request.POST.dict(),
                "COOKIES": request.COOKIES,
                "META": {k: v for k, v in request.META.items() if k.startswith("HTTP_")},
            }

            try:
                ErrorReport.objects.create(
                    school=getattr(request.user, "school", None) if request.user.is_authenticated else None,
                    user=request.user if request.user.is_authenticated else None,
                    path=request.path,
                    method=request.method,
                    exception_type=type(exc).__name__,
                    message=str(exc),
                    traceback="".join(traceback_data),
                    data=json.dumps(report_data, default=str),
                )
            except Exception:
                logger.exception("Failed to create error report")

            raise


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