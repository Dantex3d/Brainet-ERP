# schools/middleware.py

import json
import logging
import traceback
from django.shortcuts import redirect, render
from django.contrib.auth import logout
from django.urls import resolve, Resolver404
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import Http404, HttpResponse
from django.conf import settings
from django.core.mail import mail_admins
from .models import ErrorReport, SecurityLog

logger = logging.getLogger(__name__)


class ErrorReporterMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except Http404 as exc:
            self._log_security_event(request, "not_found", "Page not found", status_code=404)
            return self._render_safe_error(request, "exams/errors/404.html", {"message": "The requested page could not be found."}, 404)
        except PermissionDenied as exc:
            self._log_security_event(request, "permission_denied", "Forbidden access attempt", status_code=404)
            return self._render_safe_error(request, "exams/errors/404.html", {"message": "The requested page could not be found."}, 404)
        except SuspiciousOperation as exc:
            self._log_security_event(request, "suspicious_operation", "Suspicious request blocked", status_code=400)
            return self._render_safe_error(request, "exams/errors/400.html", {"message": "Your request could not be processed safely."}, 400)
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

            self._notify_superusers(exc, request)
            self._log_security_event(request, "server_error", "Unhandled exception captured", status_code=500, details={"exception_type": type(exc).__name__})
            return self._render_safe_error(request, "exams/errors/500.html", {"message": "A page error occurred. Our team has been notified and will investigate shortly."}, 500)

    def _render_safe_error(self, request, template_name, context, status_code):
        try:
            return render(request, template_name, context, status=status_code)
        except Exception:
            logger.exception("Failed to render friendly error page")
            return HttpResponse("A page error occurred. Our team has been notified and will investigate shortly.", status=status_code)

    def _notify_superusers(self, exc, request):
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            superusers = User.objects.filter(is_superuser=True, is_active=True)
            recipients = [user.email for user in superusers if user.email]
            if recipients:
                subject = f"Brainet error alert: {type(exc).__name__}"
                message = (
                    f"A page error occurred on {request.path} using {request.method}.\n\n"
                    f"Exception: {exc}\n\n"
                    f"User: {getattr(request.user, 'email', 'anonymous')}"
                )
                mail_admins(subject=subject, message=message, fail_silently=True)
        except Exception:
            logger.exception("Failed to notify superusers about page error")

    def _log_security_event(self, request, event_type, message, status_code=0, details=None):
        try:
            user = request.user if getattr(request, "user", None) and getattr(request.user, "is_authenticated", False) else None
            ip_address = self._get_client_ip(request)
            browser = self._get_browser_name(request.META.get("HTTP_USER_AGENT", ""))
            location = self._resolve_location(ip_address)
            SecurityLog.objects.create(
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
        except Exception:
            logger.exception("Failed to create security log")

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    def _get_browser_name(self, user_agent):
        if not user_agent:
            return "Unknown"
        user_agent_lower = user_agent.lower()
        if "edg/" in user_agent_lower:
            return "Edge"
        if "chrome" in user_agent_lower:
            return "Chrome"
        if "firefox" in user_agent_lower:
            return "Firefox"
        if "safari" in user_agent_lower:
            return "Safari"
        if "opera" in user_agent_lower:
            return "Opera"
        return "Unknown"

    def _resolve_location(self, ip_address):
        if not ip_address or ip_address in {"127.0.0.1", "localhost", "::1"}:
            return "Local environment"

        try:
            import urllib.request
            with urllib.request.urlopen(f"https://ipapi.co/{ip_address}/json/", timeout=3) as response:
                payload = json.load(response)
                city = payload.get("city") or ""
                region = payload.get("region") or ""
                country = payload.get("country_name") or payload.get("country") or ""
                parts = [part for part in [city, region, country] if part]
                return ", ".join(parts) if parts else "Unknown"
        except Exception:
            return "Unknown"


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