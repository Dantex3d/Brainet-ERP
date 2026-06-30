import datetime
from datetime import timedelta
import email
import re
from urllib import request
from django.utils import timezone
from django.conf import settings
import logging
from utils.email_service import send_email

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, get_user_model, login
from django.db import transaction
from django.db.models import Q
from django.urls import reverse

import students
import subjects
from .models import DOSMessage, DOSQuery, Notification, School, DirectorOfStudies, Dormitory, Term, Class, Subject, GradingPolicy, StudentMark, StudentPromotion, SchoolNotice
from django.db import IntegrityError
from collections import defaultdict
from students.models import Student
from schools.models import School, Dormitory, DirectorOfStudies, Term
from schools.models import Class, Subject, VoucherRequest
from classes.models import Stream
from teachers.models import ClassTeacherAssignment, Teacher, TeacherSubjectAssignment, OnlineClass, OnlineClassParticipant
from subjects.models import ClassSubject
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus import Image as RLImage
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing, Circle

User = get_user_model()
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from users.models import CustomUser
from teachers.models import Teacher


def superuser_required(view_func):
    return user_passes_test(lambda u: u.is_superuser)(view_func)

from django.conf import settings
from django.urls import reverse
from utils.email_service import send_email
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator



def send_user_verification_email(user, request=None, role_name=None):
    # Ensure user has an email
    if not getattr(user, 'email', None):
        return False

    # Resolve display name: prefer full name, then first_name, then related profile names
    display_name = None
    try:
        display_name = user.get_full_name() if user.get_full_name() else None
    except Exception:
        display_name = getattr(user, 'first_name', None)

    if not display_name:
        # Try related profiles (teacher/principal/dos)
        try:
            from teachers.models import Teacher
            t = Teacher.objects.filter(user=user).first()
            if t and getattr(t, 'name', None):
                display_name = t.name
        except Exception:
            pass

    if not display_name:
        display_name = user.email

    # =========================
    # DOS / PRINCIPAL FLOW (6-digit code)
    # =========================
    if user.role in ['dos', 'principal']:
        code = user.generate_verification_code()
        verify_link = (
            request.build_absolute_uri(reverse('verify_user_code')) + f"?email={user.email}"
            if request
            else reverse('verify_user_code') + f"?email={user.email}"
        )

        subject = f"Verify your {role_name or user.role} account on Brainet"

        html_body = f"<p>Dear {display_name},</p>"
        html_body += f"<p>Your {role_name or user.role} account has been created on Brainet.</p>"
        html_body += f"<p>Please use the verification code below (expires in 1 hour):</p>"
        html_body += f"<h2>{code}</h2>"
        html_body += f"<p>Or click here: <a href=\"{verify_link}\">Verify Account</a></p>"
        html_body += f"<p>If you did not request this, contact support.</p>"

        return send_email(to_email=user.email, subject=subject, message=html_body, recipient_name=display_name, html=True)

    # =========================
    # OTHER USERS FLOW (both code + email token link)
    # =========================
    # Generate both a short code and a token link so users may verify either way
    token = user.generate_email_verification_token()
    code = user.generate_verification_code()

    verify_link = (
        request.build_absolute_uri(reverse('verify_user_email', args=[token]))
        if request
        else reverse('verify_user_email', args=[token])
    )

    subject = f"Verify your {role_name or 'Brainet'} account"

    html_body = f"<p>Hi {display_name},</p>"
    html_body += f"<p>We've created your account on Brainet. You may verify your email using either the verification code below, or by clicking the verification link.</p>"
    html_body += f"<p><strong>Verification code:</strong></p>"
    html_body += f"<h2 style=\"letter-spacing:4px;\">{code}</h2>"
    html_body += f"<p>Or click the button to verify now:</p>"
    html_body += f"<p><a href=\"{verify_link}\" style=\"display:inline-block;padding:10px 18px;background:#0d6efd;color:#fff;border-radius:6px;text-decoration:none;\">Verify Email</a></p>"
    html_body += f"<p>If you didn't request this, ignore this email.</p>"

    return send_email(to_email=user.email, subject=subject, message=html_body, recipient_name=display_name, html=True)

def send_school_verification_email(school, request=None):
    if not school.email:
        return

    token = school.generate_verification_token()
    verify_link = request.build_absolute_uri(
        reverse('verify_school_via_token', args=[token])
    ) if request else reverse('verify_school_via_token', args=[token])

    subject = "Verify your school registration on Brainet"
    body = (
        f"Hello {school.name},\n\n"
        f"Please verify this school's email address by clicking the link below:\n\n{verify_link}\n\n"
        "This link expires in 1 hour. After verification the school admin will be able to complete activation and password resets.\n\n"
        "If you did not register this school, please ignore this message."
    )

    return send_email(
        to_email=school.email,
        subject=subject,
        message=body,
        recipient_name=school.name,
        html=False,
    )


@superuser_required
def pending_verification(request):
    """Superuser view: list users pending email verification with search and filters."""
    q = request.GET.get('q', '').strip()
    filter_type = request.GET.get('filter', '')

    users = User.objects.filter(email_verified=False)

    if q:
        users = users.filter(Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))

    if filter_type == 'failed':
        users = users.filter(verification_attempts__gt=0)

    users = users.order_by('-email_verification_sent_at')

    paginator = Paginator(users, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'schools/pending_verification.html', {
        'users': page_obj,
        'q': q,
        'filter': filter_type,
    })


@superuser_required
def pending_verification_count(request):
    count = User.objects.filter(email_verified=False).count()
    return JsonResponse({'count': count})


@superuser_required
def resend_verification_email(request, user_id):
    user = get_object_or_404(User, id=user_id)
    # Use send_user_verification_email's boolean result to determine success/failure
    try:
        sent = send_user_verification_email(user, request=request)
        if sent:
            messages.success(request, f"Verification email resent to {user.email}.")
        else:
            support = getattr(settings, 'SUPPORT_EMAIL', None) or getattr(settings, 'DEFAULT_FROM_EMAIL', None) or 'support@brainet.local'
            messages.error(request, f"Could not resend verification to {user.email}. Contact: {support}")
    except Exception as e:
        messages.error(request, f"Could not resend verification: {str(e)}")
    return redirect('pending_verification')


def contact_submit(request):
    if request.method != 'POST':
        return redirect('landing_page')

    name = request.POST.get('name', '').strip()
    email = request.POST.get('email', '').strip()
    phone = request.POST.get('phone', '').strip()
    message_text = request.POST.get('message', '').strip()

    if not name or not email or not message_text:
        messages.error(request, 'Please complete the contact form.')
        return redirect('landing_page')

    try:
        from .models import ContactMessage
        ContactMessage.objects.create(name=name, email=email, phone=phone, message=message_text)

        support = getattr(settings, 'SUPPORT_EMAIL', None) or getattr(settings, 'DEFAULT_FROM_EMAIL', None)
        subject = f"Website contact from {name}"
        body = f"Name: {name}\nEmail: {email}\nPhone: {phone}\n\nMessage:\n{message_text}"

        if support:
            sent = send_email(to_email=support, subject=subject, message=body, html=False)
            if not sent:
                messages.warning(request, f'Thank you — your message was saved, but we could not deliver notification to support. Contact: {support}')
            else:
                messages.success(request, 'Thank you — your message was sent. We will get back to you shortly.')
        else:
            messages.success(request, 'Thank you — your message was saved. We will get back to you shortly.')
    except Exception as e:
        messages.error(request, f'Could not send message: {str(e)}')

    return redirect('landing_page')


@login_required
def request_voucher(request):

    school = request.user.school

    # compute current term and student count for display
    today = timezone.now().date()
    current_term = Term.objects.filter(
        school=school,
        start_date__lte=today,
        end_date__gte=today
    ).first()

    if not current_term:
        current_term = Term.objects.filter(school=school).order_by("-start_date").first()

    term_name = current_term.name if current_term else ""
    student_count_display = Student.objects.filter(school=school).count()

    if request.method == "POST":

        # Determine current term for the school (prefer active term)
        today = timezone.now().date()
        current_term = Term.objects.filter(
            school=school,
            start_date__lte=today,
            end_date__gte=today
        ).first()

        if not current_term:
            current_term = Term.objects.filter(school=school).order_by("-start_date").first()

        term_name = current_term.name if current_term else ""

        # Count students automatically
        student_count = Student.objects.filter(school=school).count()

        VoucherRequest.objects.create(
            school=school,
            term=term_name,
            student_count=student_count,
            status="pending"
        )

        messages.success(
            request,
            "Voucher request sent successfully"
        )

        return redirect("dos_dashboard")

    # GET REQUEST
    terms = Term.objects.filter(
        school=school
    )

    context = {
        "terms": terms,
        "detected_term": term_name,
        "detected_student_count": student_count_display,
    }

    return render(
        request,
        "dashboards/request_voucher.html",
        context
    )


@login_required
def edit_notice(request, notice_id):
    notice = get_object_or_404(SchoolNotice, id=notice_id, school=request.user.school)

    # Only sender, principal or superuser can edit
    allowed = (request.user == notice.sender) or getattr(request.user, 'role', '') == 'principal' or request.user.is_superuser
    if not allowed:
        messages.error(request, "Permission denied.")
        return redirect('principal_dashboard')

    if request.method == 'POST':
        notice.title = request.POST.get('title', notice.title)
        notice.message = request.POST.get('message', notice.message)
        notice.recipient_type = request.POST.get('recipient_type', notice.recipient_type)
        notice.is_urgent = bool(request.POST.get('is_urgent'))
        notice.save()
        messages.success(request, "Announcement updated.")
        return redirect('principal_dashboard')

    return render(request, 'schools/edit_notice.html', {'notice': notice})


@login_required
def followup_notice(request, notice_id):
    notice = get_object_or_404(SchoolNotice, id=notice_id, school=request.user.school)

    # Allow principals, dos, or sender to follow up
    allowed = getattr(request.user, 'role', '') in ['principal', 'dos'] or request.user == notice.sender or request.user.is_superuser
    if not allowed:
        messages.error(request, "Permission denied.")
        return redirect('principal_dashboard')

    if request.method == 'POST':
        follow_text = request.POST.get('follow_up', '').strip()
        if follow_text:
            notice.follow_up = follow_text
            notice.followed_by = request.user
            notice.followed_at = timezone.now()
            notice.save()
            messages.success(request, "Follow-up saved.")
        else:
            messages.error(request, "Follow-up text cannot be empty.")

    return redirect('principal_dashboard')


@login_required
def delete_notice(request, notice_id):
    notice = get_object_or_404(SchoolNotice, id=notice_id, school=request.user.school)
    allowed = request.user == notice.sender or getattr(request.user, 'role', '') == 'principal' or request.user.is_superuser
    if request.method == 'POST' and allowed:
        notice.delete()
        messages.success(request, "Announcement deleted.")
    else:
        messages.error(request, "Permission denied or invalid request.")
    return redirect('principal_dashboard')

@login_required
def approve_voucher(request, id):

    voucher = get_object_or_404(
        VoucherRequest,
        id=id
    )

    voucher.status = "approved"
    voucher.save()

    messages.success(
        request,
        "Voucher approved successfully"
    )

    return redirect("superuser_dashboard")

@login_required
def superuser_dashboard(request):

    # ----------------------------
    # SCHOOLS
    # ----------------------------
    schools = School.objects.all().order_by("-id")

    active_schools = schools.filter(
        is_active=True
    ).count()

    # ----------------------------
    # APPROVED VOUCHERS
    # ----------------------------
    approved_vouchers = VoucherRequest.objects.filter(
        status="approved"
    ).order_by("-id")

    # ----------------------------
    # PENDING VOUCHERS
    # ----------------------------
    vouchers = (
        VoucherRequest.objects
        .select_related("school")
        .filter(status="pending")
        .order_by("-id")
    )

    pending_vouchers = vouchers.count()

    # ----------------------------
    # DOS MESSAGES
    # ----------------------------
    queries = (
        DOSMessage.objects
        .select_related(
            "school",
            "sender",
            "receiver"
        )
        .filter(receiver=request.user)
        .order_by("-created_at")
    )

    unread_queries = queries.filter(
        status="pending"
    ).count()

    # ----------------------------
    # ADMIN NOTIFICATIONS
    # ----------------------------
    notifications = Notification.objects.filter(recipient=request.user).order_by("-created_at")
    unread_notifications = notifications.filter(is_read=False).count()

    # ----------------------------
    # CONTEXT
    # ----------------------------
    # include pending license renewals so superusers can see reactivation requests
    from .models import LicenseRenewal
    pending_renewals = LicenseRenewal.objects.filter(status="pending").select_related("school", "requested_by").order_by("-requested_at")
    principals = Principal.objects.select_related("school").all()
    doss = DirectorOfStudies.objects.select_related("school").all()

    context = {

        "schools": schools,

        "active_schools": active_schools,

        "approved_vouchers": approved_vouchers,

        "pending_vouchers": pending_vouchers,

        "vouchers": vouchers,

        "queries": queries,

        "unread_queries": unread_queries,
        "notifications": notifications,
        "unread_notifications": unread_notifications,
        "pending_renewals": pending_renewals,
        "pending_renewals_count": pending_renewals.count(),
        "principals": principals,
        "doss": doss,
    }

    return render(
        request,
        "dashboards/superuser.html",
        context
    )


def _superuser_management_context():
    schools = School.objects.all().order_by("-id")
    principals = Principal.objects.select_related("school", "user").all().order_by("-id")
    doss = DirectorOfStudies.objects.select_related("school", "user").all().order_by("-id")

    return {
        "schools": schools,
        "principals": principals,
        "doss": doss,
    }


def _process_school_submission(request):
    action = request.POST.get("action", "create")
    school_id = request.POST.get("school_id")
    name = (request.POST.get("name") or "").strip()
    address = (request.POST.get("address") or "").strip()
    phone = (request.POST.get("phone") or "").strip()
    email = (request.POST.get("email") or "").strip()
    subscription_balance = request.POST.get("subscription_balance") or 0
    motto = (request.POST.get("motto") or "").strip()
    logo = request.FILES.get("logo")

    if not all([name, address, phone, email]):
        messages.error(request, "Please fill in all required school fields.")
        return False

    if action == "update":
        school = get_object_or_404(School, id=school_id)

        if School.objects.exclude(id=school.id).filter(name=name).exists():
            messages.warning(request, "Another school already uses that name.")
            return False

        if School.objects.exclude(id=school.id).filter(email=email).exists():
            messages.warning(request, "Another school already uses that email.")
            return False

        if School.objects.exclude(id=school.id).filter(phone=phone).exists():
            messages.warning(request, "Another school already uses that phone number.")
            return False

        school.name = name
        school.address = address
        school.phone = phone
        school.email = email
        school.motto = motto
        school.subscription_balance = subscription_balance

        if logo:
            school.logo = logo

        school.save()
        messages.success(request, f"{school.name} updated successfully.")
        return True

    if School.objects.filter(name=name).exists():
        messages.warning(request, "A school with that name already exists.")
        return False

    if School.objects.filter(email=email).exists():
        messages.warning(request, "A school with that email already exists.")
        return False

    if School.objects.filter(phone=phone).exists():
        messages.warning(request, "A school with that phone number already exists.")
        return False

    School.objects.create(
        name=name,
        address=address,
        phone=phone,
        email=email,
        motto=motto,
        subscription_balance=subscription_balance,
        logo=logo,
        is_active=False,
    )

    messages.success(request, "School added successfully.")
    messages.warning(
        request,
        "New school accounts expire within 48 hours if not activated. Contact admin to activate."
    )
    return True


def _process_principal_submission(request):
    action = request.POST.get("action", "create")
    principal_id = request.POST.get("principal_id")
    name = (request.POST.get("name") or "").strip()
    email = (request.POST.get("email") or "").strip()
    phone = (request.POST.get("phone") or "").strip()
    password = request.POST.get("password") or ""
    school_id = request.POST.get("school")

    if not all([name, email, phone, school_id]):
        messages.error(request, "Please fill all required principal fields.")
        return False

    school = get_object_or_404(School, id=school_id)

    if action == "update":
        principal = get_object_or_404(Principal, id=principal_id)
        user = principal.user

        if user and CustomUser.objects.exclude(id=user.id).filter(email=email).exists():
            messages.warning(request, "Another user already uses that email.")
            return False

        if Principal.objects.exclude(id=principal.id).filter(phone=phone).exists():
            messages.warning(request, "Another principal already uses that phone number.")
            return False

        if Principal.objects.exclude(id=principal.id).filter(school=school).exists():
            messages.warning(request, "This school already has a Principal account.")
            return False

        principal.name = name
        principal.email = email
        principal.phone = phone
        principal.school = school
        principal.save()

        if user:
            user.email = email
            user.school = school
            user.role = "principal"
            user.save(update_fields=["email", "school", "role"])

            if password:
                user.set_password(password)
                user.save(update_fields=["password"])

        messages.success(request, f"{name} updated successfully.")
        return True

    if not password:
        messages.error(request, "Password is required when creating a principal account.")
        return False

    if CustomUser.objects.filter(email=email).exists():
        messages.warning(request, "Email already taken.")
        return False

    if Principal.objects.filter(phone=phone).exists():
        messages.warning(request, "Phone number already used.")
        return False

    if Principal.objects.filter(school=school).exists():
        messages.warning(request, "This school already has a Principal account.")
        return False

    user = CustomUser.objects.create_user(
        email=email,
        password=password,
        role="principal",
        school=school,
        email_verified=False,
    )

    Principal.objects.create(
        user=user,
        school=school,
        name=name,
        email=email,
        phone=phone,
    )

    send_user_verification_email(user, request=request, role_name='Principal')
    messages.success(request, f"{name} registered successfully as Principal. A verification email has been sent.")
    return True


def _process_dos_submission(request):
    action = request.POST.get("action", "create")
    dos_id = request.POST.get("dos_id")
    name = (request.POST.get("name") or "").strip()
    email = (request.POST.get("email") or "").strip()
    phone = (request.POST.get("phone") or "").strip()
    password = request.POST.get("password") or ""
    school_id = request.POST.get("school")

    if not all([name, email, phone, school_id]):
        messages.error(request, "Please fill all required DOS fields.")
        return False

    school = get_object_or_404(School, id=school_id)

    if action == "update":
        dos = get_object_or_404(DirectorOfStudies, id=dos_id)
        user = dos.user

        if user and CustomUser.objects.exclude(id=user.id).filter(email=email).exists():
            messages.warning(request, "Another user already uses that email.")
            return False

        if DirectorOfStudies.objects.exclude(id=dos.id).filter(phone=phone).exists():
            messages.warning(request, "Another DOS already uses that phone number.")
            return False

        if DirectorOfStudies.objects.exclude(id=dos.id).filter(school=school).exists():
            messages.warning(request, "This school already has a DOS account.")
            return False

        dos.name = name
        dos.email = email
        dos.phone = phone
        dos.school = school
        dos.save()

        if user:
            user.email = email
            user.school = school
            user.role = "dos"
            user.save(update_fields=["email", "school", "role"])

            if password:
                user.set_password(password)
                user.save(update_fields=["password"])

        messages.success(request, f"{name} updated successfully.")
        return True

    if not password:
        messages.error(request, "Password is required when creating a DOS account.")
        return False

    if CustomUser.objects.filter(email=email).exists():
        messages.warning(request, "Email already taken.")
        return False

    if DirectorOfStudies.objects.filter(phone=phone).exists():
        messages.warning(request, "Phone number already used.")
        return False

    if DirectorOfStudies.objects.filter(school=school).exists():
        messages.warning(request, "This school already has a DOS account.")
        return False

    user = CustomUser.objects.create_user(
        email=email,
        password=password,
        role="dos",
        school=school,
        email_verified=False,
    )

    DirectorOfStudies.objects.create(
        user=user,
        school=school,
        name=name,
        email=email,
        phone=phone,
    )

    send_user_verification_email(user, request=request, role_name='Director of Studies')
    messages.success(request, f"{name} registered successfully. A verification email has been sent.")
    return True


@superuser_required
def manage_schools(request):
    if request.method == "POST":
        _process_school_submission(request)
        return redirect("manage_schools")

    context = _superuser_management_context()
    return render(request, "dashboards/manage_schools.html", context)


@superuser_required
def manage_principals(request):
    if request.method == "POST":
        _process_principal_submission(request)
        return redirect("manage_principals")

    context = _superuser_management_context()
    return render(request, "dashboards/manage_principals.html", context)


@superuser_required
def edit_principal_by_superuser(request, principal_id):
    principal = get_object_or_404(Principal, id=principal_id)

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        email = (request.POST.get("email") or "").strip()
        phone = (request.POST.get("phone") or "").strip()
        password = request.POST.get("password") or ""
        school_id = request.POST.get("school")

        if not all([name, email, phone, school_id]):
            messages.error(request, "Please fill all required principal fields.")
            return redirect("edit_principal_by_superuser", principal_id=principal.id)

        school = get_object_or_404(School, id=school_id)

        if CustomUser.objects.exclude(id=principal.user_id).filter(email=email).exists():
            messages.warning(request, "Another user already uses that email.")
            return redirect("edit_principal_by_superuser", principal_id=principal.id)

        if Principal.objects.exclude(id=principal.id).filter(phone=phone).exists():
            messages.warning(request, "Another principal already uses that phone number.")
            return redirect("edit_principal_by_superuser", principal_id=principal.id)

        if Principal.objects.exclude(id=principal.id).filter(school=school).exists():
            messages.warning(request, "This school already has a Principal account.")
            return redirect("edit_principal_by_superuser", principal_id=principal.id)

        principal.name = name
        principal.email = email
        principal.phone = phone
        principal.school = school
        principal.save()

        if principal.user:
            principal.user.email = email
            principal.user.school = school
            principal.user.role = "principal"
            principal.user.save(update_fields=["email", "school", "role"])

            if password:
                principal.user.set_password(password)
                principal.user.save(update_fields=["password"])

        messages.success(request, f"{name} updated successfully.")
        return redirect("manage_principals")

    context = _superuser_management_context()
    context.update({"principal": principal})
    return render(request, "dashboards/edit_principal.html", context)


@superuser_required
def delete_principal_by_superuser(request, principal_id):
    principal = get_object_or_404(Principal, id=principal_id)

    if request.method == "POST":
        principal_name = principal.name
        user = principal.user
        principal.delete()
        if user:
            user.delete()
        messages.success(request, f"{principal_name} deleted successfully.")
        return redirect("manage_principals")

    return redirect("manage_principals")


@superuser_required
def manage_dos(request):
    if request.method == "POST":
        _process_dos_submission(request)
        return redirect("manage_dos")

    context = _superuser_management_context()
    return render(request, "dashboards/manage_dos.html", context)


@superuser_required
def edit_dos_by_superuser(request, dos_id):
    dos = get_object_or_404(DirectorOfStudies, id=dos_id)

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        email = (request.POST.get("email") or "").strip()
        phone = (request.POST.get("phone") or "").strip()
        password = request.POST.get("password") or ""
        school_id = request.POST.get("school")

        if not all([name, email, phone, school_id]):
            messages.error(request, "Please fill all required DOS fields.")
            return redirect("edit_dos_by_superuser", dos_id=dos.id)

        school = get_object_or_404(School, id=school_id)

        if CustomUser.objects.exclude(id=dos.user_id).filter(email=email).exists():
            messages.warning(request, "Another user already uses that email.")
            return redirect("edit_dos_by_superuser", dos_id=dos.id)

        if DirectorOfStudies.objects.exclude(id=dos.id).filter(phone=phone).exists():
            messages.warning(request, "Another DOS already uses that phone number.")
            return redirect("edit_dos_by_superuser", dos_id=dos.id)

        if DirectorOfStudies.objects.exclude(id=dos.id).filter(school=school).exists():
            messages.warning(request, "This school already has a DOS account.")
            return redirect("edit_dos_by_superuser", dos_id=dos.id)

        dos.name = name
        dos.email = email
        dos.phone = phone
        dos.school = school
        dos.save()

        if dos.user:
            dos.user.email = email
            dos.user.school = school
            dos.user.role = "dos"
            dos.user.save(update_fields=["email", "school", "role"])

            if password:
                dos.user.set_password(password)
                dos.user.save(update_fields=["password"])

        messages.success(request, f"{name} updated successfully.")
        return redirect("manage_dos")

    context = _superuser_management_context()
    context.update({"dos": dos})
    return render(request, "dashboards/edit_dos.html", context)


@superuser_required
def delete_dos_by_superuser(request, dos_id):
    dos = get_object_or_404(DirectorOfStudies, id=dos_id)

    if request.method == "POST":
        dos_name = dos.name
        user = dos.user
        dos.delete()
        if user:
            user.delete()
        messages.success(request, f"{dos_name} deleted successfully.")
        return redirect("manage_dos")

    return redirect("manage_dos")
from django.contrib import messages
from .models import DOSQuery
from django.shortcuts import redirect
from django.contrib import messages
from .models import DOSMessage
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.shortcuts import redirect

User = get_user_model()


def send_query(request):

    if request.method == "POST":

        subject = request.POST.get("subject")
        message_text = request.POST.get("message")

        superuser = User.objects.filter(
            is_superuser=True
        ).first()

        if not superuser:

            messages.error(
                request,
                "No superuser account found"
            )

            return redirect("dos_dashboard")

        DOSMessage.objects.create(
            school=request.user.school,
            sender=request.user,
            receiver=superuser,
            subject=subject,
            message=message_text,
            parent=None,
            status="pending"
        )

        try:
            if settings.EMAIL_HOST_USER and superuser.email:
                send_email(
                    to_email=[superuser.email],
                    subject=f"DOS query: {subject}",
                    message=f"{request.user.get_full_name() or request.user.email} sent a DOS query:\n\n{message_text}",
                    recipient_name=superuser.get_full_name() or superuser.email,
                    html=False,
                )
        except Exception:
            pass

        messages.success(
            request,
            "Message sent successfully"
        )

    return redirect("dos_dashboard")

@login_required
def reply_query(request, query_id):

    query = DOSMessage.objects.get(id=query_id)

    if request.method == "POST":

        reply_message = request.POST.get("reply")

        # =========================
        # CREATE REPLY
        # =========================
        DOSMessage.objects.create(

            school=query.school,

            sender=request.user,

            receiver=query.sender,

            subject=f"RE: {query.subject}",

            message=reply_message,

            parent=query,

            status="pending"
        )

        # =========================
        # UPDATE ORIGINAL MESSAGE
        # =========================
        query.status = "replied"
        query.save()

        messages.success(
            request,
            "Reply sent successfully"
        )

        return redirect("superuser_dashboard")

def send_dos_message(request):
    if request.method == "POST":
        DOSMessage.objects.create(
            school=request.user.school,
            sender=request.user,
            receiver_id=request.POST.get("receiver"),
            subject=request.POST.get("subject"),
            message=request.POST.get("message"),
        )
        return redirect("dos_dashboard")
    
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import DOSMessage

@login_required
def reply_message(request, id):
    parent = get_object_or_404(DOSMessage, id=id)

    if request.method == "POST":
        reply_text = request.POST.get("message", "").strip()
        if not reply_text:
            messages.error(request, "Reply cannot be empty.")
            return redirect("dos_dashboard")

        # create reply
        reply = DOSMessage.objects.create(
            school=parent.school,
            sender=request.user,
            receiver=parent.sender,
            subject="RE: " + (parent.subject or "Message"),
            message=reply_text,
            parent=parent,
            status="pending"  # reply itself starts as pending for the receiver
        )

        # mark parent as replied and clear pending/unread flags for the DOS
        parent.status = "replied"
        parent.save(update_fields=["status"])

        # Optionally mark any pending replies to this parent as not unread
        # (depends on how you track unread; adjust to your model)
        DOSMessage.objects.filter(parent=parent, receiver=request.user, status="pending").update(status="read")

        messages.success(request, "Reply sent.")
        return redirect("dos_dashboard")

    # If GET, redirect back (or render a reply form if you prefer)
    return redirect("dos_dashboard")
@login_required
def clear_replied_count(request):
    DOSMessage.objects.filter(receiver=request.user, status="replied").update(status="cleared")
    messages.success(request, "Replied message count cleared.")
    return redirect("dos_dashboard")

@login_required
def clear_all_messages(request):
    """Clear all pending messages/queries for superuser and DOS"""
    if request.method == "POST":
        user = request.user
        # Mark all DOS messages as cleared
        DOSMessage.objects.filter(receiver=user).update(status="cleared")
        messages.success(request, "✓ All messages cleared successfully!")
        
        # Redirect to appropriate dashboard
        if user.is_superuser:
            return redirect("superuser_dashboard")
        else:
            return redirect("dos_dashboard")
    
    # GET request - show confirmation
    return redirect(request.META.get('HTTP_REFERER', '/'))

@login_required
def delete_single_message(request, message_id):
    """Delete a single message"""
    if request.method == "POST":
        try:
            message = DOSMessage.objects.get(id=message_id)
            if message.receiver == request.user or request.user.is_superuser:
                message.delete()
                messages.success(request, "Message deleted successfully!")
        except DOSMessage.DoesNotExist:
            messages.error(request, "Message not found.")
    
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def delete_message_completely(request, message_id):
    """Permanently delete a message and its replies."""
    if request.method == "POST":
        try:
            msg = DOSMessage.objects.get(id=message_id)
            # Only allow receiver or superuser to purge
            if msg.receiver == request.user or request.user.is_superuser:
                # delete children explicitly (FK CASCADE should handle it)
                DOSMessage.objects.filter(parent=msg).delete()
                msg.delete()
                messages.success(request, "Message permanently deleted.")
            else:
                messages.error(request, "Permission denied.")
        except DOSMessage.DoesNotExist:
            messages.error(request, "Message not found.")

    return redirect(request.META.get('HTTP_REFERER', '/'))

@login_required
def delete_message(request, message_id):
    """Delete a single message."""
    if request.method == 'POST':
        try:
            message = DOSMessage.objects.get(id=message_id)
            if message.receiver == request.user or request.user.is_superuser:
                message.delete()
                messages.success(request, "Message deleted successfully.")
            else:
                messages.error(request, "Permission denied.")
        except DOSMessage.DoesNotExist:
            messages.error(request, "Message not found.")

    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def mark_notification_read(request, notification_id):
    """Mark a single notification as read."""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()
    return redirect(request.META.get('HTTP_REFERER', 'dos_dashboard'))


@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read."""
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    messages.success(request, "All notifications have been marked as read.")
    return redirect(request.META.get('HTTP_REFERER', 'dos_dashboard'))


@login_required
def send_school_notice(request):
    """Send a notice to teachers, students, or both."""
    school = getattr(request.user, 'school', None)
    if school is None:
        messages.error(request, "You are not assigned to a school.")
        return redirect('landing_page')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        message_text = request.POST.get('message', '').strip()
        recipient_type = request.POST.get('recipient_type', 'all')
        is_urgent = bool(request.POST.get('is_urgent'))

        if not title or not message_text:
            messages.error(request, "Title and message are required.")
            return render(request, 'schools/send_notice.html', {'school': school})

        SchoolNotice.objects.create(
            school=school,
            sender=request.user,
            title=title,
            message=message_text,
            recipient_type=recipient_type,
            is_urgent=is_urgent,
        )

        messages.success(request, "School notice sent successfully.")
        return redirect('principal_dashboard')

    return render(request, 'schools/send_notice.html', {'school': school})


@login_required
def edit_school_info(request):
    """Edit the current school information."""
    school = getattr(request.user, 'school', None)
    if school is None:
        messages.error(request, "You are not assigned to a school.")
        return redirect('landing_page')

    if request.method == 'POST':
        school.name = request.POST.get('name', school.name)
        school.motto = request.POST.get('motto', school.motto)
        school.address = request.POST.get('address', school.address)
        school.email = request.POST.get('email', school.email)
        school.phone = request.POST.get('phone', school.phone)

        logo = request.FILES.get('logo')
        if logo:
            school.logo = logo

        school.save()
        messages.success(request, "School information updated successfully.")
        return redirect('principal_dashboard')

    return render(request, 'schools/edit_school_info.html', {'school': school})


@login_required
def principal_school_manager(request):
    """Principal page for editing school info and managing the school DOS account."""
    school = getattr(request.user, 'school', None)
    if school is None:
        messages.error(request, "You are not assigned to a school.")
        return redirect('landing_page')

    dos = getattr(school, 'dos', None)

    if request.method == 'POST':
        section = request.POST.get('section')

        if section == 'school':
            school.name = request.POST.get('name', school.name)
            school.motto = request.POST.get('motto', school.motto)
            school.address = request.POST.get('address', school.address)
            school.email = request.POST.get('email', school.email)
            school.phone = request.POST.get('phone', school.phone)

            logo = request.FILES.get('logo')
            if logo:
                school.logo = logo

            school.save()
            messages.success(request, "School information updated successfully.")
            return redirect('principal_school_manager')

        if section == 'dos':
            name = (request.POST.get('name') or '').strip()
            email = (request.POST.get('email') or '').strip()
            phone = (request.POST.get('phone') or '').strip()
            password = request.POST.get('password') or ''

            if not all([name, email, phone]):
                messages.error(request, "Please fill all DOS fields.")
                return redirect('principal_school_manager')

            if dos:
                user = dos.user
                if user and CustomUser.objects.exclude(id=user.id).filter(email=email).exists():
                    messages.warning(request, "Another user already uses that email.")
                    return redirect('principal_school_manager')
                if DirectorOfStudies.objects.exclude(id=dos.id).filter(phone=phone).exists():
                    messages.warning(request, "Another DOS already uses that phone number.")
                    return redirect('principal_school_manager')

                dos.name = name
                dos.email = email
                dos.phone = phone
                dos.save()

                if user:
                    user.email = email
                    user.school = school
                    user.role = 'dos'
                    user.save(update_fields=['email', 'school', 'role'])
                    if password:
                        user.set_password(password)
                        user.save(update_fields=['password'])

                messages.success(request, "DOS information updated successfully.")
                return redirect('principal_school_manager')

            if not password:
                messages.error(request, "Password is required when creating a DOS account.")
                return redirect('principal_school_manager')

            if CustomUser.objects.filter(email=email).exists():
                messages.warning(request, "Email already taken.")
                return redirect('principal_school_manager')

            if DirectorOfStudies.objects.filter(phone=phone).exists():
                messages.warning(request, "Phone number already used.")
                return redirect('principal_school_manager')

            user = CustomUser.objects.create_user(
                email=email,
                password=password,
                role='dos',
                school=school,
                email_verified=False,
            )

            DirectorOfStudies.objects.create(
                user=user,
                school=school,
                name=name,
                email=email,
                phone=phone,
            )
            send_user_verification_email(user, request=request, role_name='Director of Studies')
            messages.success(request, "DOS account created successfully. A verification email has been sent.")
            return redirect('principal_school_manager')

    return render(request, 'schools/principal_school_manager.html', {
        'school': school,
        'dos': dos,
    })


@login_required
def reset_notification_count(request):
    """Reset notification counts to zero"""
    if request.method == "POST":
        user = request.user
        # Mark all unread/pending messages as read
        DOSMessage.objects.filter(
            receiver=user,
            status__in=['pending', 'new']
        ).update(status="cleared")
        
        messages.success(request, "✓ Notifications reset to zero!")
        
        if user.is_superuser:
            return redirect("superuser_dashboard")
        else:
            return redirect("dos_dashboard")
    
    return redirect(request.META.get('HTTP_REFERER', '/'))

    
def landing_page(request):
    # Show verified schools carousel and testimonials on landing
    schools_list = School.objects.filter(is_verified=True).order_by('-created_at')[:12]
    # Simple static testimonials; could be replaced by a model later
    testimonials = [
        {"author": "St. Mary's High", "text": "Brainet transformed our reporting and saved hours each week."},
        {"author": "Green Valley Academy", "text": "Reliable, fast and great support."},
        {"author": "Sunrise School", "text": "Teachers love the online class features and easy grading."},
    ]
    return render(request, "dashboards/landing.html", {"schools_list": schools_list, "testimonials": testimonials})

@login_required
def features_demo(request):
    """Demo page showcasing new features for customers"""
    return render(request, "schools/features_demo.html")


def contact_admin(request):
    """Simple page instructing users to contact their administrator."""
    return render(request, "schools/contact_admin.html")

def view_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    return render(request, "dos/view_students.html", {"student": student})


@login_required
def dos_dashboard(request):
    school = request.user.school

    # =========================
    # BASIC DATA
    # =========================
    classes = Class.objects.filter(school=school)
    students = Student.objects.filter(school=school)
    subjects = Subject.objects.filter(school=school)
    exams = Exam.objects.filter(school=school).order_by("-created_at")

    # =========================
    # DOS MESSAGES (both sent and received)
    # =========================
    dos_messages = DOSMessage.objects.filter(
        school=school,
        parent__isnull=True
    ).order_by("-created_at")

    # only unread replies to DOS
    unread_messages = DOSMessage.objects.filter(
        school=school,
        receiver=request.user,
        status="pending"
    ).count()

    # =========================
    # VOUCHER REQUESTS
    # =========================
    vouchers = VoucherRequest.objects.filter(school=school).order_by("-id")
    pending_vouchers = vouchers.filter(status="pending").count()
    approved_vouchers = vouchers.filter(status="approved").count()
    rejected_vouchers = vouchers.filter(status="rejected").count()

    # =========================
    # CONTEXT
    # =========================
    context = {
        "school": school,
        "classes": classes,
        "students": students,
        "subjects": subjects,
        "exams": exams,
        "dos_messages": dos_messages,
        "unread_messages": unread_messages,
        "vouchers": vouchers,
        "pending_vouchers": pending_vouchers,
        "approved_vouchers": approved_vouchers,
        "rejected_vouchers": rejected_vouchers,
        # Notices for staff
        "notices": SchoolNotice.objects.filter(school=school).filter(recipient_type__in=['teachers','all']).order_by('-created_at'),
    }

    return render(request, "dashboards/dos.html", context)
from exams.models import Exam
from django.db.models import Avg, Count
@login_required
def principal_dashboard(request):
    school = request.user.school

    # Counts
    student_count = Student.objects.filter(school=school).count()
    teacher_count = Teacher.objects.filter(school=school).count()
    dorm_count = Dormitory.objects.filter(school=school).count()

    # Performance: average marks per subject
    subject_performance = (
        Mark.objects.filter(student__school=school)
        .values("subject__name")
        .annotate(avg_score=Avg("score"), student_count=Count("student"))
        .order_by("subject__name")
    )

    # Pending reports (example: assume Report model)
    from reports.models import Report
    # Pending reports


    return render(request, "dashboards/principal.html", {
        "school": school,
        "student_count": student_count,
        "teacher_count": teacher_count,
        "dorm_count": dorm_count,
        "subject_performance": subject_performance,
        "notices_sent": SchoolNotice.objects.filter(school=school).order_by('-created_at'),
        "notices": SchoolNotice.objects.filter(school=school).order_by('-created_at'),
    })

@login_required
def class_list_selector(request):
    """Select class and stream to export/preview class list"""
    school = request.user.school
    
    classes = Class.objects.filter(school=school).order_by("level", "name")
    teacher_restricted = False
    teacher_assignments = None
    assigned_class_ids = []
    
    teacher = Teacher.objects.filter(user=request.user, school=school).first()
    if teacher:
        teacher_assignments = ClassTeacherAssignment.objects.filter(
            teacher=teacher
        ).select_related("class_obj", "stream")
        if teacher_assignments.exists():
            teacher_restricted = True
            assigned_class_ids = list(teacher_assignments.values_list("class_obj_id", flat=True))
            classes = classes.filter(id__in=assigned_class_ids)
    
    streams = []
    selected_class = None
    
    if request.GET.get("class_id"):
        selected_class_id = request.GET.get("class_id")
        selected_class_qs = Class.objects.filter(id=selected_class_id, school=school)
        if teacher_restricted:
            selected_class_qs = selected_class_qs.filter(id__in=assigned_class_ids)
        selected_class = get_object_or_404(selected_class_qs)
        streams = Stream.objects.filter(class_group=selected_class).order_by("name")
        if teacher_restricted and teacher_assignments is not None:
            valid_stream_ids = list(
                teacher_assignments.filter(class_obj=selected_class).values_list("stream_id", flat=True)
            )
            streams = streams.filter(id__in=valid_stream_ids)
    
    return render(request, "dos/class_list_selector.html", {
        "school": school,
        "classes": classes,
        "streams": streams,
        "selected_class": selected_class,
        "teacher_restricted": teacher_restricted,
    })
    
from django.db.models import Count

@login_required
def manage_classes(request):
    school = request.user.school

    classes = (
        Class.objects
        .filter(school=school)
        .annotate(
            student_count=Count("students"),
            stream_count=Count("streams")
        )
        .prefetch_related("streams")
        .order_by("level")
    )

    teachers = Teacher.objects.filter(school=school)
    subjects = Subject.objects.filter(school=school)

    return render(
        request,
        "dos/classes.html",
        {
            "classes": classes,
            "teachers": teachers,
            "subjects": subjects,
        }
    )


@login_required
def assign_class_master(request):
    """Assign a teacher as class master to a class or stream"""
    if request.method == "POST":
        school = request.user.school
        class_id = request.POST.get("class_id")
        stream_id = request.POST.get("stream_id")
        teacher_id = request.POST.get("class_master")

        class_obj = get_object_or_404(Class, id=class_id, school=school)

        if stream_id:
            # Assign to specific stream
            stream = get_object_or_404(Stream, id=stream_id, class_group=class_obj)
            # Update ClassTeacherAssignment for this stream
            if teacher_id:
                teacher = get_object_or_404(Teacher, id=teacher_id, school=school)
                ClassTeacherAssignment.objects.update_or_create(
                    class_obj=class_obj,
                    stream=stream,
                    defaults={"teacher": teacher}
                )
                messages.success(request, f"Stream master assigned successfully.")
            else:
                ClassTeacherAssignment.objects.filter(
                    class_obj=class_obj,
                    stream=stream
                ).delete()
                messages.success(request, "Stream master removed.")
        else:
            # Assign to entire class
            if teacher_id:
                teacher = get_object_or_404(Teacher, id=teacher_id, school=school)
                class_obj.class_master = teacher
                class_obj.save()
                messages.success(request, f"Class master assigned successfully.")
            else:
                class_obj.class_master = None
                class_obj.save()
                messages.success(request, "Class master removed.")

    return redirect("manage_classes")


@login_required
def add_class_subject(request):
    """Add subjects to a class"""
    if request.method == "POST":
        school = request.user.school
        class_id = request.POST.get("class_id")
        subject_ids = request.POST.getlist("subject_id")

        class_obj = get_object_or_404(Class, id=class_id, school=school)

        # Get all currently assigned subjects
        current_subjects = set(
            ClassSubject.objects.filter(class_name=class_obj).values_list("subject_id", flat=True)
        )

        new_subject_ids = set(int(sid) for sid in subject_ids if sid)

        # Remove subjects not in the new list
        to_remove = current_subjects - new_subject_ids
        if to_remove:
            ClassSubject.objects.filter(class_name=class_obj, subject_id__in=to_remove).delete()

        # Add new subjects
        for subject_id in new_subject_ids - current_subjects:
            subject = get_object_or_404(Subject, id=subject_id, school=school)
            ClassSubject.objects.get_or_create(
                school=school,
                class_name=class_obj,
                subject=subject
            )

        messages.success(request, "Subjects assigned successfully.")

    return redirect("manage_classes")


@login_required
def add_stream(request):
    """Add a stream/division to a class"""
    if request.method == "POST":
        school = request.user.school
        class_id = request.POST.get("class_id")
        stream_name = request.POST.get("stream_name", "").strip()

        class_obj = get_object_or_404(Class, id=class_id, school=school)

        if stream_name:
            # Check if stream already exists
            existing = Stream.objects.filter(
                class_group=class_obj,
                name=stream_name
            ).first()

            if existing:
                messages.warning(request, f"Stream '{stream_name}' already exists for this class.")
            else:
                Stream.objects.create(class_group=class_obj, name=stream_name)
                messages.success(request, f"Stream '{stream_name}' added successfully.")
        else:
            messages.error(request, "Stream name cannot be empty.")

    return redirect("manage_classes")
    
    
@login_required
def add_class(request):
    if request.method == "POST":
        name = request.POST.get("name")
        level = request.POST.get("level")
        stream = request.POST.get("stream")  # <-- capture stream
        # Save class and optional stream
        school = request.user.school

        new_class = Class.objects.create(
            name=name,
            level=level,
            school=school
        )

        # create a Stream if provided
        if stream:
            from classes.models import Stream
            Stream.objects.create(class_group=new_class, name=stream)

        messages.success(request, f"Class {name} created successfully!")
        return redirect("manage_classes")
    return render(request, "dos/add_class.html")

def edit_class(request, class_id):
    c = get_object_or_404(Class, id=class_id)
    teachers = Teacher.objects.all()

    if request.method == "POST":
        c.name = request.POST.get("name")
        c.level = request.POST.get("level")
        c.stream = request.POST.get("stream")
        teacher_id = request.POST.get("teacher")
        c.teacher_id = teacher_id if teacher_id else None
        c.save()
        messages.success(request, "Class updated successfully!")
        return redirect("manage_classes")

    # Pass class object + teachers to template
    return render(request, "dos/edit_class.html", {
        "class_obj": c,
        "teachers": teachers
    })

@login_required
def delete_class(request, class_id):
    school = request.user.school

    school_class = get_object_or_404(
        Class,
        id=class_id,
        school=school
    )

    if request.method == 'POST':
        school_class.delete()
        messages.success(request, "Class deleted successfully.")
        return redirect("manage_classes")

    # Only allow POST deletes
    return redirect("manage_classes")

@login_required
@login_required
def view_class_students(request, class_id):
    """
    View students in a class with optional stream selection.
    Allows DOS/class teacher to select and view students, then export to PDF.
    """
    school = request.user.school
    
    school_class = get_object_or_404(
        Class,
        id=class_id,
        school=school
    )
    
    # Get all streams for this class
    streams = Stream.objects.filter(class_group=school_class).order_by("name")
    
    # Get selected stream if provided
    stream_id = request.GET.get("stream_id")
    selected_stream = None
    
    if stream_id:
        selected_stream = get_object_or_404(Stream, id=stream_id, class_group=school_class)

    # Restrict class teachers to their assigned stream(s) for this class
    teacher_assignments = ClassTeacherAssignment.objects.filter(
        teacher__user=request.user,
        class_obj=school_class
    ).select_related("stream")
    teacher_restricted = teacher_assignments.exists()
    if teacher_restricted:
        valid_stream_ids = list(teacher_assignments.values_list("stream_id", flat=True))
        streams = streams.filter(id__in=valid_stream_ids)
        if not selected_stream or selected_stream.id not in valid_stream_ids:
            selected_stream = Stream.objects.filter(id=valid_stream_ids[0]).first()
    
    # Get students based on selection
    student_query = Student.objects.filter(
        school=school,
        current_class=school_class
    )
    
    # Filter by stream if selected
    if selected_stream:
        students = student_query.filter(stream=selected_stream).order_by("name")
        display_title = f"{school_class.name} - {selected_stream.name}"
    else:
        # If no stream selected, show all unstreamed students
        students = student_query.filter(stream__isnull=True).order_by("name")
        display_title = f"{school_class.name}"
    
    # Count statistics
    total_students = students.count()
    male_count = students.filter(gender__iexact="Male").count()
    female_count = students.filter(gender__iexact="Female").count()
    
    return render(request, "dos/view_class_students.html", {
        "school": school,
        "school_class": school_class,
        "streams": streams,
        "selected_stream": selected_stream,
        "students": students,
        "display_title": display_title,
        "total_students": total_students,
        "male_count": male_count,
        "female_count": female_count,
        "teacher_restricted": teacher_restricted,
    })
    
@login_required 
def manage_students(request):
    school = request.user.school

    students = Student.objects.filter(school=school)

    classes = Class.objects.filter(school=school)
    streams = Stream.objects.filter(class_group__school=school)
    dorms = Dormitory.objects.filter(school=school)
    return render(request, "dos/manage_students.html", {
        "students": students,
        "classes": classes,
        "streams": streams,
        "dorms": dorms,
    })

from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from classes.models import Class, Stream
from students.models import Student
from django.contrib.auth import get_user_model

User = get_user_model()
@login_required
def get_class_streams(request):
    """API endpoint: Return streams as JSON for a selected class"""
    import json
    from django.http import JsonResponse
    
    class_id = request.GET.get('class_id')
    school = request.user.school
    
    if not class_id:
        return JsonResponse({'streams': []})
    
    try:
        class_obj = Class.objects.get(id=class_id, school=school)
        streams = Stream.objects.filter(class_group=class_obj).values('id', 'name')
        return JsonResponse({
            'streams': list(streams),
            'success': True
        })
    except Class.DoesNotExist:
        return JsonResponse({'streams': [], 'success': False})

@login_required
def add_student(request):

    school = request.user.school

    classes = Class.objects.filter(school=school)
    dormitory = Dormitory.objects.filter(school=school)

    if request.method == "POST":

        name = request.POST.get("name")
        admission_number = request.POST.get("admission_number")
        gender = request.POST.get("gender")
        class_id = request.POST.get("class_id")
        stream_id = request.POST.get("stream_id")
        dorm_id = request.POST.get("dorm_id")

        # =========================
        # CLASS
        # =========================
        school_class = get_object_or_404(Class, id=class_id, school=school)

        # =========================
        # STREAM (OPTIONAL)
        # =========================
        stream = None
        if stream_id:
            stream = get_object_or_404(Stream, id=stream_id, class_group=school_class)

        # =========================
        # DORM (OPTIONAL)
        # =========================
        dorm = None
        if dorm_id:
            dorm = get_object_or_404(Dormitory, id=dorm_id, school=school)

        # =========================
        # EMAIL LOGIN SYSTEM
        # =========================
        email = f"{admission_number}@{school.name.lower().replace(' ', '')}.school"

        if User.objects.filter(email=email).exists():
            messages.error(request, "Student already exists")
            return redirect("add_student")

        # =========================
        # CREATE USER
        # =========================
        user = User.objects.create_user(
            email=email,
            password=admission_number,
            school=school,
            role="student"
        )

        # =========================
        # CREATE STUDENT PROFILE
        # =========================
        Student.objects.create(
            user=user,
            school=school,
            name=name,
            admission_number=admission_number,
            gender=gender,
            current_class=school_class,
            stream=stream,
            dormitory=dorm
        )

        messages.success(
            request,
            f"Student created successfully! Login: {email} / {admission_number}"
        )

        return redirect("manage_students")

    return render(request, "dos/add_student.html", {
        "classes": classes,
        "dorms": dormitory,
    })

@login_required
def edit_student(request, student_id):
    school = request.user.school

    student = get_object_or_404(
        Student,
        id=student_id,
        school=school
    )

    if request.method == "POST":
        student.name = request.POST.get("name")
        student.admission_number = request.POST.get("admission_number")
        student.gender = request.POST.get("gender")

        # ======================
        # CLASS
        # ======================
        class_id = request.POST.get("class_id")
        student.current_class = get_object_or_404(
            Class,
            id=class_id,
            school=school
        )

        # ======================
        # STREAM (OPTIONAL)
        # ======================
        stream_id = request.POST.get("stream_id")
        if stream_id:
            student.stream = get_object_or_404(
                Stream,
                id=stream_id,
                class_group=student.current_class
            )
        else:
            student.stream = None

        # ======================
        # DORMITORY (OPTIONAL)
        # ======================
        dorm_id = request.POST.get("dormitory_id")
        if dorm_id:
            student.dormitory = get_object_or_404(
                Dormitory,
                id=dorm_id,
                school=school
            )
        else:
            student.dormitory = None

        student.save()
        messages.success(request, "Student updated successfully.")
        return redirect("manage_students")

    # for form dropdowns
    classes = Class.objects.filter(school=school)
    streams = Stream.objects.filter(class_group__school=school)
    dorms = Dormitory.objects.filter(school=school)

    return render(request, "dos/edit_student.html", {
        "student": student,
        "classes": classes,
        "streams": streams,
        "dorms": dorms,
    })

def delete_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)

    if request.method == "POST":
        student.delete()

    return redirect("manage_students")
    
  
def download_student_list(request):
    school = request.user.school

    students = Student.objects.filter(school=school)

    return HttpResponse("Student list download will be implemented here.")  
@login_required
def manage_dorms(request):
    school = request.user.school

    return render(request, "dos/dorms.html", {
        "dorms": Dormitory.objects.filter(school=school)
    })
    
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from students.models import Student
from .models import StudentMark
from assignments.models import Submission, Assignment


@login_required
def student_dashboard(request):

    # =========================
    # GET STUDENT PROFILE
    # =========================
    student = get_object_or_404(
        Student,
        user=request.user,
        school=request.user.school
    )

    school = student.school

    # =========================
    # CLASS DATA
    # =========================
    current_class = student.current_class
    current_stream = student.stream

    # =========================
    # SUBJECTS (FROM CLASS OR SCHOOL)
    # =========================
    subjects = Subject.objects.filter(
        school=school
    )

    # =========================
    # ASSIGNMENTS
    # =========================
    assignments = Assignment.objects.filter(
        school=school,
        class_assigned=current_class,
        is_active=True
    ).order_by("-created_at")

    # =========================
    # SUBMISSIONS
    # =========================
    submissions = Submission.objects.filter(
        student=student
    ).select_related("assignment")

    # =========================
    # ASSIGNMENT STATUS
    # =========================
    submissions_by_assignment = {s.assignment_id: s for s in submissions}
    assignments_with_status = []
    for assignment in assignments:
        submission = submissions_by_assignment.get(assignment.id)
        assignments_with_status.append({
            "assignment": assignment,
            "is_submitted": bool(submission),
            "is_graded": submission.status == "graded" if submission else False,
            "score": submission.score if submission and submission.score is not None else None,
            "feedback": submission.feedback if submission else "",
            "submission": submission,
        })

    marked_assignments = [item for item in assignments_with_status if item["is_graded"]]

    marks = StudentMark.objects.filter(
        student=student
    ).select_related("subject").order_by("-created_at")

    average = 0
    if marks.exists():
        total_score = sum([float(mark.marks) for mark in marks if mark.marks is not None])
        average = round(total_score / marks.count(), 1) if marks.count() else 0

    online_classes = OnlineClass.objects.filter(
        school=school,
        class_obj=current_class
    ).filter(
        Q(stream__isnull=True) | Q(stream=current_stream)
    ).select_related("teacher", "subject", "class_obj", "stream").order_by("start_time")

    for online_class in online_classes:
        OnlineClassParticipant.objects.get_or_create(
            online_class=online_class,
            student=student,
        )

    participant_records = OnlineClassParticipant.objects.filter(
        student=student,
        online_class__in=online_classes
    ).select_related("online_class")
    participant_map = {p.online_class_id: p for p in participant_records}

    online_class_view = []
    for online_class in online_classes:
        participant = participant_map.get(online_class.id)
        online_class_view.append({
            "online_class": online_class,
            "participant": participant,
            "status": participant.status if participant else "not_tried",
        })

    # =========================
    # CONTEXT
    # =========================
    return render(request, "students/dashboard.html", {
        "student": student,
        "class": current_class,
        "stream": current_stream,
        "subjects": subjects,
        "assignments": assignments,
        "assignments_with_status": assignments_with_status,
        "marked_assignments": marked_assignments,
        "submissions": submissions,
        "marks": marks,
        "average": average,
        "online_classes": online_class_view,
        "notices": SchoolNotice.objects.filter(school=school).filter(recipient_type__in=['students','all']).order_by('-created_at'),
    })

def add_dorm(request):
    school = request.user.school

    if request.method == "POST":
        Dormitory.objects.create(
            name=request.POST.get("name"),
            capacity=request.POST.get("capacity"),
            supervisor=request.POST.get("supervisor"),
            school=school
        )
        messages.success(request, "Dormitory added successfully.")
        return redirect("manage_dorms")  
    return render(request, "dos/add_dorm.html")


@login_required
def student_online_class_action(request, online_class_id):
    student = get_object_or_404(
        Student,
        user=request.user,
        school=request.user.school
    )

    online_class = get_object_or_404(
        OnlineClass,
        id=online_class_id,
        school=student.school
    )

    participant, _ = OnlineClassParticipant.objects.get_or_create(
        online_class=online_class,
        student=student,
    )

    action = request.POST.get("action")
    if action == "join":
        participant.status = "joined"
        participant.joined_at = timezone.now()
        participant.save()
        messages.success(request, "You have joined the class.")
    elif action == "fail":
        participant.status = "failed"
        participant.save()
        messages.error(request, "Marked as failed to join.")

    return redirect("student_dashboard")

@login_required
def view_dorm_students(request, dorm_id):
    school = request.user.school

    dorm = get_object_or_404(Dormitory, id=dorm_id, school=school)

    students = Student.objects.filter(
        school=school,
        dormitory=dorm
    )

    return render(request, "dos/dorm_list.html", {
        "dorm": dorm,
        "students": students
    })
def edit_dorm(request, dorm_id):
        school = request.user.school

        dorm = get_object_or_404(Dormitory, id=dorm_id, school=school)

        if request.method == "POST":
            dorm.name = request.POST.get("name")
            dorm.capacity = request.POST.get("capacity")
            dorm.supervisor = request.POST.get("supervisor")
            dorm.save()

            messages.success(request, "Dormitory updated successfully.")
            return redirect("manage_dorms")

        return render(request, "dos/edit_dorm.html", {
            "dorm": dorm
        })
        
def dormitory_lists(request):
    school = request.user.school

    dorms = Dormitory.objects.filter(school=school)

    return render(request, "dos/dormitory_lists.html", {
        "dorms": dorms
    })
    
def delete_dorm(request, dorm_id):
    school = request.user.school

    dorm = get_object_or_404(Dormitory, id=dorm_id, school=school)

    if request.method == "POST":
        dorm.delete()
        messages.success(request, "Dormitory deleted successfully.")
        return redirect("manage_dorms")

    return render(request, "dos/delete_dorm.html", {
        "dorm": dorm
    })

@login_required
def print_class_list(request, class_id):
    
    class_obj = get_object_or_404(Class, id=class_id)

    students = Student.objects.filter(current_class_id=class_id)

    return render(request, "classes/print_class_list.html", {
        "class_obj": class_obj,
        "students": students
    })
import os
from django.conf import settings
from django.http import HttpResponse
from reportlab.platypus import PageBreak, SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph, Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
import datetime
import os

@login_required
def download_class_list_pdf(request, class_id):
    """
    Export class list to PDF with proper stream filtering and professional styling.
    Ensures students are only included if they belong to the selected class/stream.
    """

    # =========================
    # GET CLASS & STREAM
    # =========================
    class_obj = get_object_or_404(Class, id=class_id)
    stream_id = request.GET.get("stream_id")
    term_id = request.GET.get("term")
    
    school = class_obj.school
    
    selected_stream = None
    if stream_id:
        selected_stream = get_object_or_404(Stream, id=stream_id, class_group=class_obj)

    # Restrict class teachers to their assigned stream for this class
    class_teacher_assignments = ClassTeacherAssignment.objects.filter(
        teacher__user=request.user,
        class_obj=class_obj
    ).select_related("stream")
    if class_teacher_assignments.exists():
        valid_stream_ids = list(class_teacher_assignments.values_list("stream_id", flat=True))
        if not selected_stream or selected_stream.id not in valid_stream_ids:
            selected_stream = Stream.objects.filter(id=valid_stream_ids[0]).first()

    # =========================
    # GET STUDENTS - STRICT FILTERING
    # =========================
    student_query = Student.objects.filter(
        current_class=class_obj,
        school=school
    )
    
    # If stream is selected, ONLY include students from that stream
    if selected_stream:
        student_query = student_query.filter(stream=selected_stream)
    else:
        # If no stream selected, exclude students who have a stream assigned
        # (only include unstreamed students)
        student_query = student_query.filter(stream__isnull=True)
    
    students = student_query.order_by("name")

    # =========================
    # BUILD FILE NAME WITH CLASS & STREAM (BETTER FORMAT)
    # =========================
    now = datetime.datetime.now()
    year = now.year
    date_str = now.strftime("%Y%m%d")
    
    # Format filename as: Grade10-East_ClassList_Term2_2026.pdf or Grade10_ClassList_General_2026.pdf
    if selected_stream and term_id:
        term_obj = Term.objects.filter(id=term_id).first()
        term_name = term_obj.name if term_obj else f"Term{term_id}"
        # Replace spaces with underscores and clean up name
        class_name_clean = class_obj.name.replace(" ", "")
        stream_name_clean = selected_stream.name.replace(" ", "")
        term_name_clean = term_name.replace(" ", "")
        filename = f"{class_name_clean}-{stream_name_clean}_ClassList_{term_name_clean}_{year}.pdf"
        display_title = f"{class_obj.name} {selected_stream.name}"
    elif selected_stream:
        class_name_clean = class_obj.name.replace(" ", "")
        stream_name_clean = selected_stream.name.replace(" ", "")
        filename = f"{class_name_clean}-{stream_name_clean}_ClassList_{year}.pdf"
        display_title = f"{class_obj.name} {selected_stream.name}"
    elif term_id:
        term_obj = Term.objects.filter(id=term_id).first()
        term_name = term_obj.name if term_obj else f"Term{term_id}"
        class_name_clean = class_obj.name.replace(" ", "")
        term_name_clean = term_name.replace(" ", "")
        filename = f"{class_name_clean}_ClassList_{term_name_clean}_{year}.pdf"
        display_title = f"{class_obj.name}"
    else:
        class_name_clean = class_obj.name.replace(" ", "")
        filename = f"{class_name_clean}_ClassList_General_{year}.pdf"
        display_title = f"{class_obj.name}"

    folder_path = os.path.join(
        settings.MEDIA_ROOT,
        "class_lists"
    )

    os.makedirs(folder_path, exist_ok=True)
    file_path = os.path.join(folder_path, filename)

    # =========================
    # CREATE PDF DOCUMENT
    # =========================
    pagesize = landscape(A4) if term_id else A4
    
    doc = SimpleDocTemplate(
        file_path,
        pagesize=pagesize,
        rightMargin=25,
        leftMargin=25,
        topMargin=35,
        bottomMargin=30,
        title=display_title
    )

    styles = getSampleStyleSheet()
    elements = []

    # =========================
    # HEADER WITH LOGO & SCHOOL INFO
    # =========================
    header_data = []
    logo_image = None

    # Add logo if available
    if school.logo and os.path.exists(school.logo.path):
        try:
            logo_image = Image(
                school.logo.path,
                width=2.5 * cm,
                height=2.5 * cm
            )
        except Exception:
            pass

    # Build header content with school name underlined
    stream_info = f"<b>Stream:</b> {selected_stream.name}" if selected_stream else ""
    
    header_text = f"""
    <font size='18'><b>{school.name.upper()}</b></font><br/>
    <hr width="100%" noshade="1" thickness="2"/><br/>
    <font size='13'><b>OFFICIAL CLASS LIST</b></font><br/>
    <font size='11'>Class: <b>{class_obj.name}</b>&nbsp;&nbsp;&nbsp;{stream_info}</font><br/>
    <font size='10'>Academic Year: {year}</font><br/>
    <font size='9'>Generated: {now.strftime("%d %B %Y at %H:%M")}</font>
    """

    header_paragraph = Paragraph(header_text, styles["Normal"])
    
    if logo_image:
        header_table = Table(
            [[logo_image, header_paragraph]],
            colWidths=[2.5 * cm, None]
        )
    else:
        header_table = Table(
            [[header_paragraph]],
            colWidths=[None]
        )

    header_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    elements.append(header_table)
    elements.append(Spacer(1, 0.4 * cm))

    # =========================
    # STUDENT COUNT SUMMARY
    # =========================
    summary_text = f"""
    <font size='10'><b>Total Students: {students.count()}</b>&nbsp;&nbsp;&nbsp;
    Male: {students.filter(gender="Male").count()}&nbsp;&nbsp;&nbsp;
    Female: {students.filter(gender="Female").count()}</font>
    """
    summary_para = Paragraph(summary_text, styles["Normal"])
    elements.append(summary_para)
    elements.append(Spacer(1, 0.2 * cm))

    # =========================
    # BUILD STUDENT TABLE
    # =========================
    if term_id:
        # Include academic details with marks
        subjects = Subject.objects.filter(school=school).order_by("name")
        marks_qs = StudentMark.objects.filter(
            student__in=students,
            term_id=term_id
        ).select_related("subject")
        
        mark_map = {
            (mark.student_id, mark.subject_id): mark
            for mark in marks_qs
        }
        
        # Build header row
        data = [["#", "Student Name", "Admission No", "Gender"]]
        for subject in subjects:
            data[0].append(subject.short_name)
        data[0].extend(["Total", "Avg", "Grade"])
        
        # Build student rows
        for i, student in enumerate(students, start=1):
            row = [str(i), student.name, student.admission_number, student.gender]
            
            total_marks = 0
            total_subjects = 0
            
            for subject in subjects:
                mark = mark_map.get((student.id, subject.id))
                if mark:
                    marks_value = int(round(mark.marks))
                    row.append(str(marks_value))
                    total_marks += marks_value
                    total_subjects += 1
                else:
                    row.append("-")
            
            average = round(total_marks / total_subjects, 1) if total_subjects > 0 else 0
            
            # Get grade
            grade_obj = GradingPolicy.objects.filter(
                school=school,
                min_score__lte=average,
                max_score__gte=average
            ).first()
            
            grade_letter = grade_obj.short_form if grade_obj else "-"
            row.extend([str(total_marks), str(average), grade_letter])
            data.append(row)
        
        # Calculate column widths for landscape
        col_count = len(data[0])
        subject_cols = len(subjects)
        col_widths = [0.5*cm, 4*cm, 2*cm, 1.2*cm] + [0.8*cm] * subject_cols + [1*cm, 1*cm, 0.8*cm]
        
        table = Table(data, colWidths=col_widths)
    else:
        # Basic table without marks (portrait)
        data = [[
            "#",
            "Student Name",
            "Admission No",
            "Gender"
        ]]

        for i, student in enumerate(students, start=1):
            data.append([
                str(i),
                student.name,
                student.admission_number,
                student.gender
            ])

        table = Table(
            data,
            colWidths=[0.8*cm, 8*cm, 3*cm, 1.5*cm]
        )

    # Professional table styling with alternating row colors
    table_style = [
        # HEADER
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9 if term_id else 10),
        ("PADDING", (0, 0), (-1, 0), 8),
        
        # ALTERNATING ROW COLORS
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
        
        # GRID
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
        
        # FONT
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8 if term_id else 9),
        
        # PADDING
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        
        # ALIGNMENT
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
    ]
    
    table.setStyle(TableStyle(table_style))
    elements.append(table)

    elements.append(Spacer(1, 0.3 * cm))

    # =========================
    # STATISTICS FOOTER
    # =========================
    total_students = students.count()
    male_students = students.filter(gender__iexact="Male").count()
    female_students = students.filter(gender__iexact="Female").count()

    stats_text = f"""
    <b>Summary:</b> Total Students: <b>{total_students}</b> 
    &nbsp;&nbsp;|&nbsp;&nbsp;
    Male: <b>{male_students}</b> 
    &nbsp;&nbsp;|&nbsp;&nbsp;
    Female: <b>{female_students}</b>
    """

    stats_para = Paragraph(stats_text, styles["Normal"])
    elements.append(stats_para)

    elements.append(Spacer(1, 0.2 * cm))

    # =========================
    # FOOTER
    # =========================
    footer_text = f"""
    <font size='8'><i>Generated by Brainet ERP System | {now.strftime("%d-%m-%Y %H:%M")} | Classification: Official Record</i></font>
    """
    footer_para = Paragraph(footer_text, styles["Normal"])
    elements.append(footer_para)

    # =========================
    # BUILD PDF
    # =========================
    doc.build(elements)

    # =========================
    # RETURN DOWNLOAD RESPONSE
    # =========================
    with open(file_path, "rb") as pdf_file:
        response = HttpResponse(
            pdf_file.read(),
            content_type="application/pdf"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
from django.shortcuts import get_object_or_404, render
from students.models import Student

def student_report(request, student_id):
    student = get_object_or_404(Student, id=student_id)

    # later we will attach marks, exams, etc.
    return render(request, "students/report.html", {
        "student": student
    })
    
def class_lists(request, class_id):
    school = request.user.school

    school_class = get_object_or_404(
        Class,
        id=class_id,
        school=school
    )

    students = Student.objects.filter(
        school=school,
        current_class=school_class
    ) 

    return render(request, "dos/class_list.html", {
        "school_class": school_class,
        "students": students
    })

@login_required
def class_list_preview(request, class_id):
    """Preview class list with academic details (marks, grades, points)"""
    school = request.user.school
    term_id = request.GET.get("term")
    
    school_class = get_object_or_404(Class, id=class_id, school=school)
    
    students = Student.objects.filter(
        school=school,
        current_class=school_class,
        status="active"
    ).select_related("stream").order_by("name")
    
    subjects = Subject.objects.filter(school=school).order_by("name")
    
    preview_rows = []
    
    if term_id:
        # Get all marks for this class and term
        marks_qs = StudentMark.objects.filter(
            student__in=students,
            term_id=term_id
        ).select_related("subject")
        
        mark_map = {
            (mark.student_id, mark.subject_id): mark
            for mark in marks_qs
        }
        
        for student in students:
            subject_scores = []
            total_marks = 0
            total_subjects = 0
            total_points = 0
            
            for subject in subjects:
                mark = mark_map.get((student.id, subject.id))
                
                if mark is not None:
                    marks_value = int(round(mark.marks))
                    total_marks += marks_value
                    total_subjects += 1
                    if mark.points:
                        total_points += mark.points
                else:
                    marks_value = None
                
                subject_scores.append(marks_value)
            
            average = round(total_marks / total_subjects, 2) if total_subjects > 0 else 0
            
            # Get grade
            grade_obj = GradingPolicy.objects.filter(
                school=school,
                min_score__lte=average,
                max_score__gte=average
            ).first()
            
            preview_rows.append({
                "student": student,
                "stream_name": student.stream.name if student.stream else "",
                "subject_scores": subject_scores,
                "total": total_marks,
                "average": average,
                "grade": grade_obj.short_form if grade_obj else "-",
                "points": total_points,
            })
        
        # Sort by total descending
        preview_rows.sort(key=lambda x: x["total"], reverse=True)
        
        # Add rank
        for idx, row in enumerate(preview_rows, start=1):
            row["rank"] = idx
    
    # Get terms for dropdown
    terms = Term.objects.filter(school=school).order_by("-id")
    selected_term = None
    if term_id:
        selected_term = Term.objects.filter(id=term_id).first()
    
    return render(request, "dos/class_list_preview.html", {
        "school_class": school_class,
        "students": students,
        "subjects": subjects,
        "preview_rows": preview_rows,
        "terms": terms,
        "selected_term": selected_term,
        "term_id": term_id,
    })
    
def edit_school(request, school_id):
    school = get_object_or_404(School, id=school_id)

    if request.method == "POST":
        school.name = request.POST.get("name")
        school.address = request.POST.get("address")
        school.phone = request.POST.get("phone")
        school.email = request.POST.get("email")
        school.logo  = request.FILES.get("logo") or school.logo
        
        school.save()

        messages.success(request, "School details updated successfully.")
        return redirect("view_school", school_id=school.id)

    return render(request, "dos/edit_school.html", {
        "school": school
    })
    
def view_school(request, school_id):
    school = get_object_or_404(School, id=school_id)

    return render(request, "dos/view_school.html", {
        "school": school
    })  
@login_required
def create_staff(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        role = request.POST.get("role")
        school_id = request.POST.get("school_id")

        school = get_object_or_404(School, id=school_id)

        # AUTO USERNAME
        username = email.split("@")[0]

        # Use your CustomUser model
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password="password123",   # or generate random
            role=role,
            school=school
        )

        # Save extra fields
        user.first_name = name
        user.save()

        send_user_verification_email(user, request=request, role_name=role.replace('_', ' ').title())

        messages.success(
            request,
            f"{role.replace('_', ' ').title()} account created successfully. A verification email has been sent."
        )

        return redirect("superuser_dashboard")

    # If GET, render form
    schools = School.objects.all()
    return render(request, "schools/create_staff.html", {"schools": schools})


def manage_staff(request):
    school = request.user.school

    staff = CustomUser.objects.filter(school=school).exclude(is_superuser=True)

    return render(request, "dos/staff.html", {
        "staff": staff
    })
    
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from users.models import CustomUser
from .models import School, DirectorOfStudies, Principal


@login_required
def register_dos_by_superuser(request):

    if request.method == "POST":

        try:

            name = request.POST.get("name")
            email = request.POST.get("email")
            phone = request.POST.get("phone")
            password = request.POST.get("password")
            school_id = request.POST.get("school")

            # VALIDATION
            if not all([name, email, phone, password, school_id]):

                messages.error(
                    request,
                    "Please fill all required fields."
                )

                return redirect("superuser_dashboard")

            school = School.objects.get(id=school_id)

            # EMAIL EXISTS
            if CustomUser.objects.filter(email=email).exists():

                messages.warning(
                    request,
                    "Email already taken."
                )

                return redirect("superuser_dashboard")

            # PHONE EXISTS
            if DirectorOfStudies.objects.filter(phone=phone).exists():

                messages.warning(
                    request,
                    "Phone number already used."
                )

                return redirect("superuser_dashboard")

            # SCHOOL ALREADY HAS DOS
            if DirectorOfStudies.objects.filter(school=school).exists():

                messages.warning(
                    request,
                    "This school already has a DOS account."
                )

                return redirect("superuser_dashboard")

            # CREATE USER (initially unverified)
            user = User.objects.create_user(
            email=email,
            password=password,
            role="dos",
            school=school,
            email_verified=False  # Must verify via code before full access

            )

            # CREATE DOS PROFILE
            DirectorOfStudies.objects.create(
                user=user,
                school=school,
                name=name,
                email=email,
                phone=phone
            )

            send_user_verification_email(user, request=request, role_name='Director of Studies')

            messages.success(
                request,
                f"{name} registered successfully. A verification email has been sent."
            )

        except School.DoesNotExist:

            messages.error(
                request,
                "Selected school does not exist."
            )

        except IntegrityError:

            messages.error(
                request,
                "Duplicate information detected."
            )

        except Exception as e:

            messages.error(
                request,
                f"System Error: {str(e)}"
            )

    return redirect("superuser_dashboard")
@login_required
def register_principal_by_superuser(request):
    if request.method == "POST":
        try:
            name = request.POST.get("name")
            email = request.POST.get("email")
            phone = request.POST.get("phone")
            password = request.POST.get("password")
            school_id = request.POST.get("school")

            # VALIDATION
            if not all([name, email, phone, password, school_id]):
                messages.error(request, "Please fill all required fields.")
                return redirect("superuser_dashboard")

            school = School.objects.get(id=school_id)

            # EMAIL EXISTS
            if CustomUser.objects.filter(email=email).exists():
                messages.warning(request, "Email already taken.")
                return redirect("superuser_dashboard")

            # PHONE EXISTS
            if Principal.objects.filter(phone=phone).exists():
                messages.warning(request, "Phone number already used.")
                return redirect("superuser_dashboard")

            # SCHOOL ALREADY HAS PRINCIPAL
            if Principal.objects.filter(school=school).exists():
                messages.warning(request, "This school already has a Principal account.")
                return redirect("superuser_dashboard")

            # CREATE USER (initially unverified)
            user = CustomUser.objects.create_user(
                email=email,
                password=password,
                role="principal",
                school=school,
                email_verified=False  # Must verify via code before full access
            )

            # CREATE PRINCIPAL PROFILE
            Principal.objects.create(
                user=user,
                school=school,
                name=name,
                email=email,
                phone=phone
            )

            send_user_verification_email(user, request=request, role_name='Principal')

            messages.success(request, f"{name} registered successfully as Principal. A verification email has been sent.")

        except School.DoesNotExist:
            messages.error(request, "Selected school does not exist.")

        except IntegrityError:
            messages.error(request, "Duplicate information detected.")

        except Exception as e:
            messages.error(request, f"System Error: {str(e)}")

    return redirect("superuser_dashboard")

def activate_school(request, school_id):
    school = get_object_or_404(School, id=school_id)
    school.is_active = True
    school.is_verified = True
    school.verified_at = timezone.now()
    if hasattr(request.user, 'email'):
        school.verified_by = request.user
    school.save()

    email_subject = f"School verified: {school.name}"
    email_body = (
        f"The school '{school.name}' has been verified and activated by {request.user.get_full_name() or request.user.email}.\n"
        f"School email: {school.email}\n"
        f"Phone: {school.phone}\n"
    )

    try:
        if settings.EMAIL_HOST_USER and school.email:
            send_email(
                to_email=[school.email],
                subject=email_subject,
                message=email_body,
                recipient_name=school.name,
                html=False,
            )
        for su in User.objects.filter(is_superuser=True):
            if su.email:
                send_email(
                    to_email=[su.email],
                    subject=email_subject,
                    message=email_body,
                    recipient_name=su.get_full_name() or su.email,
                    html=False,
                )
    except Exception:
        pass

    messages.success(request, "School activated and verified successfully.")
    return redirect("view_school", school_id=school.id)


def verify_school_via_token(request, token):
    school = get_object_or_404(School, verification_token=token)

    if not school.verification_sent_at or school.verification_sent_at + timedelta(hours=1) < timezone.now():
        school.verification_token = None
        school.save(update_fields=["verification_token"])
        messages.error(request, "School verification link has expired. Please request a new school registration email.")
        return redirect("register_school")

    school.is_verified = True
    school.verified_at = timezone.now()
    school.verification_token = None
    school.save(update_fields=["is_verified", "verified_at", "verification_token"])
    messages.success(request, "School email verified successfully. A school administrator will complete activation soon.")
    return redirect("register_school_success")

def active_schools(request):
    schools = School.objects.filter(is_active=True)
    return render(request, "dos/active_schools.html", {
        "schools": schools
    })
    
@login_required
def deactivate_school(request, school_id):
    """Deactivate a school and redirect to deactivation page"""
    school = get_object_or_404(School, id=school_id)
    
    if request.method == "POST":
        reason = request.POST.get("reason", "")
        school.is_active = False
        school.license_status = 'suspended'
        school.deactivated_at = timezone.now()
        school.deactivation_reason = reason
        school.save()
        messages.success(request, "School has been deactivated.")
        return redirect("school_deactivated", school_id=school.id)
    
    context = {'school': school}
    return render(request, "schools/deactivate_confirm.html", context)

@login_required
def school_deactivated(request, school_id):
    """Page shown when school is deactivated"""
    school = get_object_or_404(School, id=school_id)
    
    # Check if user has permission to view this page (superuser, DOS, or Principal)
    if not (
        request.user.is_superuser or 
        (hasattr(request.user, 'dos_profile') and request.user.dos_profile.school_id == school_id) or
        (hasattr(request.user, 'principal') and request.user.principal.school_id == school_id)
    ):
        return redirect("landing_page")
    
    pending_renewals = school.license_renewals.filter(status='pending').select_related('requested_by')
    context = {
        'school': school,
        'has_pending_renewal': pending_renewals.exists(),
        'pending_renewals': pending_renewals,
    }
    return render(request, "schools/school_deactivated.html", context)

@login_required
def request_license_renewal(request, school_id):
    """Request license renewal"""
    from .models import LicenseRenewal
    
    school = get_object_or_404(School, id=school_id)
    
    # Check permission
    if not (request.user.is_superuser or 
            (hasattr(request.user, 'dos_profile') and request.user.dos_profile.school_id == school_id) or
            (hasattr(request.user, 'principal') and request.user.principal.school_id == school_id)):
        return redirect("landing_page")
    
    if request.method == "POST":
        renewal_period = request.POST.get("renewal_period", "365")
        
        LicenseRenewal.objects.create(
            school=school,
            requested_by=request.user,
            renewal_period_days=int(renewal_period)
        )
        # Notify DOS and superusers about the renewal request
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            superusers = User.objects.filter(is_superuser=True)

            title = "License renewal requested"
            message_text = f"{request.user.get_full_name() or request.user.email} requested license renewal for {school.name}."

            # notify each superuser
            for su in superusers:
                Notification.objects.create(
                    school=school,
                    sender=request.user,
                    recipient=su,
                    title=title,
                    message=message_text
                )

            # notify school's DOS (if assigned)
            dos = getattr(school, 'dos', None)
            if dos and getattr(dos, 'user', None):
                Notification.objects.create(
                    school=school,
                    sender=request.user,
                    recipient=dos.user,
                    title=title,
                    message=message_text
                )
        except Exception:
            pass
        
        messages.success(request, "License renewal request submitted. Please wait for approval.")
        return redirect("school_deactivated", school_id=school.id)
    
    context = {'school': school}
    return render(request, "schools/request_renewal.html", context)

@login_required
def approve_license_renewal(request, renewal_id):
    """Superuser approval for license renewal"""
    from .models import LicenseRenewal
    
    if not request.user.is_superuser:
        return redirect("landing_page")
    
    renewal = get_object_or_404(LicenseRenewal, id=renewal_id)
    
    if request.method == "POST":
        approval_status = request.POST.get("status")
        notes = request.POST.get("notes", "")
        
        renewal.status = approval_status
        renewal.processed_by = request.user
        renewal.processed_at = timezone.now()
        renewal.notes = notes
        renewal.save()
        
        if approval_status == 'approved':
            # Activate school and extend license
            school = renewal.school
            school.is_active = True
            school.license_status = 'active'
            school.license_expiry = timezone.now().date() + timedelta(days=renewal.renewal_period_days)
            school.deactivated_at = None
            school.save()
            
            messages.success(request, f"License renewed for {school.name} until {school.license_expiry}")
        else:
            messages.info(request, "License renewal has been rejected.")
        
        return redirect("superuser_dashboard")
    
    context = {'renewal': renewal}
    return render(request, "schools/approve_renewal.html", context)

@superuser_required
def add_school(request):
    if request.method == "POST":
        name = request.POST.get("name")
        address = request.POST.get("address")
        phone = request.POST.get("phone")
        email = request.POST.get("email")
        subscription_balance = request.POST.get("subscription_balance") or 0
        logo = request.FILES.get("logo")

        logger = logging.getLogger(__name__)
        try:
            School.objects.create(
                name=name,
                address=address,
                phone=phone,
                email=email,
                subscription_balance=subscription_balance,
                logo=logo,
                is_active=False,
            )
            messages.success(request, "School added successfully.")
            messages.warning(
                request,
                "New school accounts expire within 48 hours if not activated. Contact admin to activate."
            )
        except (OSError, IOError) as e:
            # Likely running on a read-only filesystem (serverless). Create record without logo
            logger.exception("Failed to save uploaded logo file for school: %s", e)
            school = School.objects.create(
                name=name,
                address=address,
                phone=phone,
                email=email,
                subscription_balance=subscription_balance,
                is_active=False,
            )
            messages.success(request, "School added, but logo upload failed.")
            messages.error(request, "Logo could not be saved on this server. Configure remote media storage (S3/GCS) and try again.")

    return redirect("superuser_dashboard")


def register_school(request):
    if request.method == "POST":
        name = request.POST.get("name")
        address = request.POST.get("address")
        phone = request.POST.get("phone")
        email = request.POST.get("email")

        if not name or not address or not phone or not email:
            messages.error(request, "Please fill in all required fields.")
            return render(request, "schools/register_school.html", {
                "name": name,
                "address": address,
                "phone": phone,
                "email": email,
            })

        if School.objects.filter(email=email).exists():
            messages.error(request, "A school with this email already exists.")
            return render(request, "schools/register_school.html", {
                "name": name,
                "address": address,
                "phone": phone,
                "email": email,
            })

        school = School.objects.create(
            name=name,
            address=address,
            phone=phone,
            email=email,
            is_active=False,
        )

        send_school_verification_email(school, request=request)

        try:
            superusers = User.objects.filter(is_superuser=True)
            sender = superusers.first() if superusers.exists() else None
            title = "New school registration request"
            message_text = (
                f"A new school registration request has been submitted for '{school.name}'. "
                f"Contact: {phone}, {email}."
            )
            for su in superusers:
                Notification.objects.create(
                    school=school,
                    sender=sender or su,
                    recipient=su,
                    title=title,
                    message=message_text,
                )
                if settings.EMAIL_HOST_USER and su.email:
                    try:
                        send_email(
                            to_email=[su.email],
                            subject=title,
                            message=message_text,
                            recipient_name=su.get_full_name() or su.email,
                            html=False,
                        )
                    except Exception:
                        pass
        except Exception:
            pass

        messages.success(
            request,
            "Thank you. Your school registration request has been submitted. An admin will activate it within 48 hours."
        )
        return redirect("register_school_success")

    return render(request, "schools/register_school.html")


def register_school_success(request):
    return render(request, "schools/register_school_success.html")

def manage_schools(request):
    schools = School.objects.all()

    return render(request, "schools/schools.html", {
        "schools": schools
    })
    
    
def view_school(request, school_id):
    school = get_object_or_404(School, id=school_id)

    return render(request, "schools/view_school.html", {
        "school": school
    })
    
def edit_school(request, school_id):
    school = get_object_or_404(School, id=school_id)

    if request.method == "POST":
        school.name = request.POST.get("name")
        school.address = request.POST.get("address")
        school.phone = request.POST.get("phone")
        school.email = request.POST.get("email")
        school.save()

        messages.success(request, "School details updated successfully.")
        return redirect("view_school", school_id=school.id)

    return render(request, "schools/edit_school.html", {
        "school": school
    })
    
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

from .models import School


def delete_school(request, school_id):

    school = get_object_or_404(
        School,
        id=school_id
    )

    try:
        school.delete()

        messages.success(
            request,
            "School deleted successfully."
        )

    except Exception as e:

        messages.error(
            request,
            f"Delete failed: {str(e)}"
        )

    return redirect("superuser_dashboard")
    
def manage_terms(request):
    school = request.user.school

    terms = Term.objects.filter(school=school)

    return render(request, "dos/terms.html", {
        "terms": terms
    })  

def open_exam_window(request):
    school = request.user.school

    # This is a placeholder function. The actual implementation would depend on how you manage exam windows in your models.
    messages.info(request, "Exam window opened successfully.")
    return redirect("dos_dashboard")
def close_exam_window(request):
    school = request.user.school

    # This is a placeholder function. The actual implementation would depend on how you manage exam windows in your models.
    messages.info(request, "Exam window closed successfully.")
    return redirect("dos_dashboard")
from django.shortcuts import render, redirect
from django.contrib import messages

from exams.models import Exam, ExamSubject, Mark
from schools.models import Subject, Term
from django.contrib import messages
from django.shortcuts import redirect, render

@login_required
def manage_exams(request):

    school = request.user.school

    terms = Term.objects.filter(
        school=school
    )

    subjects = Subject.objects.filter(
        school=school
    )

    exams = Exam.objects.filter(
        school=school
    ).order_by("-created_at")

    if request.method == "POST":

        try:

            name = request.POST.get("name")
            term_id = request.POST.get("term")
            exam_type = request.POST.get("exam_type")

            subject_ids = request.POST.getlist(
                "subjects"
            )

            # CREATE EXAM
            exam = Exam.objects.create(
                school=school,
                name=name,
                term_id=term_id,
                exam_type=exam_type
            )

            # ATTACH SUBJECTS
            for subject_id in subject_ids:

                ExamSubject.objects.create(
                    exam=exam,
                    subject_id=subject_id
                )

            messages.success(
                request,
                "Exam created successfully."
            )

            return redirect("manage_exams")

        except Exception as e:

            messages.error(
                request,
                f"System Error: {str(e)}"
            )

    return render(
        request,
        "dos/manage_exams.html",
        {
            "terms": terms,
            "subjects": subjects,
            "exams": exams,
        }
    )
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction

@login_required
def enter_marks(request):

    school = request.user.school

    # =========================
    # LOAD DATA (SCHOOL SAFE)
    # =========================
    classes = Class.objects.filter(school=school).order_by("name")
    subjects = Subject.objects.filter(school=school).order_by("name")
    terms = Term.objects.filter(school=school).order_by("name")

    # =========================
    # GET FILTERS
    # =========================
    selected_class = request.GET.get("class")
    selected_subject = request.GET.get("subject")
    selected_term = request.GET.get("term")

    students = Student.objects.none()

    # =========================
    # LOAD STUDENTS SAFELY
    # =========================
    if selected_class:
        students = Student.objects.filter(
            school=school,
            current_class_id=selected_class
        ).order_by("name")

    # =========================
    # SAVE MARKS
    # =========================
    if request.method == "POST":

        class_id = request.POST.get("class")
        subject_id = request.POST.get("subject")
        term_id = request.POST.get("term")

        # -------------------------
        # VALIDATION
        # -------------------------
        if not class_id or not subject_id or not term_id:
            messages.error(request, "Class, Subject and Term are required")
            return redirect("enter_marks")

        # -------------------------
        # SAFE OBJECTS
        # -------------------------
        subject = Subject.objects.filter(id=subject_id, school=school).first()
        term = Term.objects.filter(id=term_id, school=school).first()

        if not subject or not term:
            messages.error(request, "Invalid subject or term selected")
            return redirect("enter_marks")

        grading = GradingPolicy.objects.filter(school=school)

        saved_count = 0

        # -------------------------
        # LOOP MARKS
        # -------------------------
        for key, value in request.POST.items():

            if key.startswith("mark_"):

                student_id = key.split("_")[1]

                student = Student.objects.filter(
                    id=student_id,
                    school=school
                ).first()

                if not student:
                    continue

                try:
                    marks = float(value)
                except:
                    marks = 0

                if marks < 0 or marks > 100:
                    continue

                grade_obj = grading.filter(
                    min_score__lte=marks,
                    max_score__gte=marks
                ).first()

                StudentMark.objects.update_or_create(
                    student=student,
                    subject=subject,
                    term=term,
                    defaults={
                        "marks": marks,
                        "grade": grade_obj.grade_letter if grade_obj else "",
                        "points": grade_obj.points if grade_obj else 0
                    }
                )

                saved_count += 1

        messages.success(request, f"{saved_count} marks saved successfully")

        return redirect(
            f"/schools/principal/enter-marks/?class={class_id}&subject={subject_id}&term={term_id}"
        )

    # =========================
    # RENDER
    # =========================
    return render(request, "exams/enter_marks.html", {
        "classes": classes,
        "subjects": subjects,
        "terms": terms,
        "students": students,
        "selected_class": selected_class,
        "selected_subject": selected_subject,
        "selected_term": selected_term,
    })

def report_center(request):
    
    classes = Class.objects.all()
    exams = Exam.objects.all()

    students = []

    class_id = request.GET.get("class_id")

    if class_id:

        students = Student.objects.filter(class_name_id=class_id)

    context = {
        "classes": classes,
        "students": students,
        "exams": exams,
    }

    return render(
        request,
        "exams/report_center.html",
        context
    )

    
@login_required
def marksheet_preview(request):

    school = request.user.school

    class_id = request.GET.get("class")
    term_id = request.GET.get("term")
    stream_id = request.GET.get("stream")

    students = []
    subjects = []
    report_rows = []
    selected_stream = None
    streams = []
    display_title = ""

    if class_id:
        # Get all streams for this class
        streams = Stream.objects.filter(class_group_id=class_id).order_by("name")
        
        if stream_id:
            selected_stream = get_object_or_404(Stream, id=stream_id, class_group_id=class_id)
            class_obj = get_object_or_404(Class, id=class_id)
            display_title = f"{class_obj.name} {selected_stream.name} - Marksheet"
        else:
            class_obj = get_object_or_404(Class, id=class_id)
            display_title = f"{class_obj.name} - Marksheet"

    if class_id and term_id:

        # =====================================
        # ALL STUDENTS IN CLASS / STREAM
        # =====================================
        student_query = Student.objects.filter(
            school=school,
            current_class_id=class_id,
            status="active"
        )

        if selected_stream:
            student_query = student_query.filter(stream=selected_stream)

        students = student_query.select_related("stream").order_by("name")

        # =====================================
        # ALL SUBJECTS
        # =====================================
        subjects = Subject.objects.filter(
            school=school
        ).order_by("name")

        marks_qs = StudentMark.objects.filter(
            student__in=students,
            term_id=term_id
        ).select_related("subject")

        mark_map = {
            (mark.student_id, mark.subject_id): mark
            for mark in marks_qs
        }

        for student in students:

            subject_scores = []
            total_marks = 0
            total_subjects = 0
            total_points = 0

            for subject in subjects:

                mark = mark_map.get((student.id, subject.id))

                if mark is not None:
                    marks_value = int(round(mark.marks))
                    total_marks += marks_value
                    total_subjects += 1
                    # Add points from each subject
                    if mark.points:
                        total_points += mark.points
                else:
                    marks_value = None

                subject_scores.append(marks_value)

            average = round(total_marks / total_subjects, 2) if total_subjects > 0 else 0

            grade_obj = GradingPolicy.objects.filter(
                school=school,
                min_score__lte=average,
                max_score__gte=average
            ).first()

            report_rows.append({
                "student": student,
                "stream_name": student.stream.name if student.stream else "",
                "subject_scores": subject_scores,
                "total": total_marks,
                "average": average,
                "grade": grade_obj.short_form if grade_obj else "-",
                "points": total_points,
            })

        # =====================================
        # SORT BY TOTAL DESCENDING
        # =====================================
        report_rows.sort(
            key=lambda x: x["total"],
            reverse=True
        )

        # =====================================
        # POSITIONS
        # =====================================
        for idx, row in enumerate(report_rows, start=1):
            row["position"] = idx

        # =====================================
        # STREAM RANKING
        # =====================================
        streams_by_rank = defaultdict(list)

        for row in report_rows:
            streams_by_rank[row["stream_name"]].append(row)

        for stream_rows in streams_by_rank.values():
            stream_rows.sort(key=lambda x: x["total"], reverse=True)
            for idx, row in enumerate(stream_rows, start=1):
                row["stream_rank"] = idx

    # =====================================
    # COUNTS
    # =====================================
    total_students = len(students)

    boys = students.filter(
        gender="Male"
    ).count()

    girls = students.filter(
        gender="Female"
    ).count()

    return render(
        request,
        "dos/marksheet_preview.html",
        {
            "school": school,
            "subjects": subjects,
            "report_rows": report_rows,
            "total_students": total_students,
            "boys": boys,
            "girls": girls,
            "class_id": class_id,
            "term_id": term_id,
            "stream_id": stream_id,
            "selected_stream": selected_stream,
            "streams": streams,
            "display_title": display_title,
        }
    )

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Spacer,
    Paragraph,
    Image
)

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch

from datetime import date

from schools.models import School, Class, Subject, Term
from students.models import Student
from schools.models import GradingPolicy




# =========================================================
# USE YOUR SAVED GRADING SYSTEM
# =========================================================
def get_grade_and_points(school, mark):

    grading = GradingPolicy.objects.filter(
        school=school,
        min_score__lte=mark,
        max_score__gte=mark
    ).first()

    if grading:
        return grading.short_form or grading.grade_letter, grading.points

    return "-", 0


# =========================================================
# EXPORT PDF
# =========================================================
@login_required
def export_marksheet_pdf(request):

    class_id = request.GET.get("class")
    term_id = request.GET.get("term")
    stream_id = request.GET.get("stream")

    school = request.user.school

    class_obj = get_object_or_404(
        Class,
        id=class_id,
        school=school
    )

    term_obj = get_object_or_404(
        Term,
        id=term_id,
        school=school
    )

    selected_stream = None
    if stream_id:
        selected_stream = get_object_or_404(Stream, id=stream_id, class_group=class_obj)

    subjects = Subject.objects.filter(
        school=school
    )

    student_query = Student.objects.filter(
        school=school,
        current_class_id=class_id
    )

    if selected_stream:
        student_query = student_query.filter(stream=selected_stream)

    students = student_query.select_related("stream").order_by("name")

    marks = StudentMark.objects.filter(
        student__in=students,
        term_id=term_id
    ).select_related(
        "student",
        "subject"
    )


    if selected_stream:
        class_teacher_assignment = ClassTeacherAssignment.objects.filter(
            class_obj=class_obj,
            stream=selected_stream
        ).select_related("teacher").first()
    else:
        class_teacher_assignment = ClassTeacherAssignment.objects.filter(
            class_obj=class_obj
        ).select_related("teacher").first()

    # =====================================================
    # RESPONSE
    # =====================================================
    response = HttpResponse(content_type="application/pdf")

    response["Content-Disposition"] = (
        f'attachment; filename="marksheet_{class_obj.name}.pdf"'
    )

    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        leftMargin=20,
        rightMargin=20,
        topMargin=20,
        bottomMargin=20,
    )

    styles = getSampleStyleSheet()

    elements = []

    # =====================================================
    # SCHOOL HEADER WITH LOGO ON LEFT
    # =====================================================
    school_info = f"""
    <b>{school.name}</b><br/>
    {school.address if school.address else ''}<br/>
    Phone: {school.phone if school.phone else ''}<br/>
    Email: {school.email if school.email else ''}
    """

    header_paragraph = Paragraph(
        school_info,
        styles["Normal"]
    )

    logo = ""

    if school.logo:
        try:
            logo = Image(
                school.logo.path,
                width=0.8 * inch,
                height=0.8 * inch
            )
        except:
            logo = ""

    # Logo on left, school info on right
    header_table = Table(
        [[logo, header_paragraph]],
        colWidths=[100, 650]
    )

    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(header_table)
    elements.append(Spacer(1, 8))

    # =====================================================
    # CLASS INFO BELOW HEADER
    # =====================================================
    class_label = class_obj.name
    if selected_stream:
        class_label = f"{class_obj.name} - {selected_stream.name}"
    else:
        class_label = f"{class_obj.name}"

    class_info = Paragraph(
        f"<b>MARKSHEET:</b> {class_label} | <b>TERM:</b> {term_obj.name} | <b>YEAR:</b> {date.today().year}",
        styles["Normal"]
    )
    elements.append(class_info)
    elements.append(Spacer(1, 10))
    elements.append(Spacer(1, 12))

    # =====================================================
    # TABLE HEADER
    # =====================================================
    table_data = []

    header = [
        "ADM NO",
        "NAME",
        "GENDER"
    ]

    for subject in subjects:
        header.append(subject.short_name.upper())

    header += [
        "TOTAL",
        "AVG",
        "GRADE",
        "POINTS",
        "RANK"
    ]

    table_data.append(header)

    # =====================================================
    # BUILD STUDENT RESULTS
    # =====================================================
    ranking_data = []

    for student in students:

        row = [
            student.admission_number,
            student.name,
            student.gender
        ]

        total_marks = 0
        total_subject_points = 0
        subject_count = 0

        for subject in subjects:

            mark_obj = StudentMark.objects.filter(
                student=student,
                subject=subject,
                term_id=term_id
            ).first()

            if mark_obj:

                mark = int(mark_obj.marks)

                total_marks += mark
                subject_count += 1

                grade, points = get_grade_and_points(
                    school,
                    mark
                )

                total_subject_points += points

                row.append(int(mark))

            else:
                row.append("-")

        # =================================================
        # TOTALS
        # =================================================
        average = 0

        if subject_count > 0:
            average = total_marks / subject_count

        final_grade, avg_points = get_grade_and_points(
            school,
            average
        )

        ranking_data.append({
            "student": student,
            "row": row,
            "total": total_marks,
            "average": average,
            "grade": final_grade,
            "points": total_subject_points,
        })

    # =====================================================
    # RANKING
    # =====================================================
    ranking_data = sorted(
        ranking_data,
        key=lambda x: x["total"],
        reverse=True
    )

    current_rank = 1

    for item in ranking_data:

        row = item["row"]

        row += [
            int(item["total"]),
            round(item["average"], 1),
            item["grade"],
            int(item["points"]),
            current_rank
        ]

        table_data.append(row)

        current_rank += 1

    # =====================================================
    # CREATE TABLE
    # =====================================================
    table = Table(table_data, repeatRows=1)

    table.setStyle(TableStyle([
        # GRID
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        # HEADER BOLD
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        # FONTSIZE
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        # CENTER ALIGN
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        # VERTICAL MIDDLE
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        # PADDING
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        # STUDENT NAME LEFT ALIGN
        ("ALIGN", (1, 1), (1, -1), "LEFT"),
    ]))

    elements.append(table)

    # =====================================================
    # FOOTER
    # =====================================================
    elements.append(Spacer(1, 20))

    footer = Paragraph(
        f"""
        Generated by Brainet Analytics School System<br/>
        Printed on: {date.today()}
        """,
        styles["Normal"]
    )

    elements.append(footer)

    # =====================================================
    # GRADE ANALYSIS (NEW PAGE)
    # =====================================================
    elements.append(PageBreak())

    analysis_title = Paragraph("<b>GRADE ANALYSIS</b>", styles["Heading2"])
    elements.append(analysis_title)
    elements.append(Spacer(1, 15))

    # Separate by gender
    males = [r for r in ranking_data if getattr(r["student"], "gender", "").lower() in ["m", "male"]]
    females = [r for r in ranking_data if getattr(r["student"], "gender", "").lower() in ["f", "female"]]

    # =====================================================
    # TOP 5 BOYS TABLE
    # =====================================================
    elements.append(Paragraph("<b>TOP 5 BOYS</b>", styles["Heading3"]))
    elements.append(Spacer(1, 8))
    
    top5_boys_data = [["ADM NO", "NAME", "TOTAL", "AVG", "GRADE"]]
    for item in males[:5]:
        s = item["student"]
        top5_boys_data.append([
            s.admission_number,
            s.name,
            int(item["total"]),
            round(item["average"], 1),
            item["grade"]
        ])

    boys_table = Table(top5_boys_data, colWidths=[80, 150, 70, 60, 60])
    boys_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(boys_table)
    elements.append(Spacer(1, 20))

    # =====================================================
    # TOP 5 GIRLS TABLE
    # =====================================================
    elements.append(Paragraph("<b>TOP 5 GIRLS</b>", styles["Heading3"]))
    elements.append(Spacer(1, 8))
    
    top5_girls_data = [["ADM NO", "NAME", "TOTAL", "AVG", "GRADE"]]
    for item in females[:5]:
        s = item["student"]
        top5_girls_data.append([
            s.admission_number,
            s.name,
            int(item["total"]),
            round(item["average"], 1),
            item["grade"]
        ])

    girls_table = Table(top5_girls_data, colWidths=[80, 150, 70, 60, 60])
    girls_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(girls_table)
    elements.append(Spacer(1, 20))

    # =====================================================
    # GRADE DISTRIBUTION TABLE
    # =====================================================
    elements.append(Paragraph("<b>OVERALL GRADE DISTRIBUTION</b>", styles["Heading3"]))
    elements.append(Spacer(1, 8))
    
    grade_counts = {}
    for item in ranking_data:
        g = item["grade"]
        grade_counts[g] = grade_counts.get(g, 0) + 1

    grade_dist_data = [["GRADE", "COUNT"]]
    for k, v in sorted(grade_counts.items(), reverse=True):
        grade_dist_data.append([k, v])

    grade_table = Table(grade_dist_data, colWidths=[100, 80])
    grade_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(grade_table)
    elements.append(Spacer(1, 20))

    # =====================================================
    # BEST PER SUBJECT TABLE
    # =====================================================
    elements.append(Paragraph("<b>BEST PERFORMER PER SUBJECT</b>", styles["Heading3"]))
    elements.append(Spacer(1, 8))
    
    best_data = [["SUBJECT", "BEST STUDENT", "ADM NO", "MARK"]]

    for subject in subjects:
        subj_marks = marks.filter(subject=subject)
        if subj_marks.exists():
            best_mark_obj = subj_marks.order_by('-marks').first()
            best_data.append([
                subject.name,
                best_mark_obj.student.name,
                best_mark_obj.student.admission_number,
                int(best_mark_obj.marks)
            ])
        else:
            best_data.append([subject.name, "-", "-", "-"])

    best_table = Table(best_data, colWidths=[100, 150, 80, 60])
    best_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(best_table)
    elements.append(Spacer(1, 20))

    # =====================================================
    # SUBJECT GRADE DISTRIBUTION TABLE
    # =====================================================
    elements.append(Paragraph("<b>SUBJECT GRADE DISTRIBUTION</b>", styles["Heading3"]))
    elements.append(Spacer(1, 8))
    
    all_grade_letters = set()
    subject_grade_counts = {}

    for subject in subjects:
        subj_marks = marks.filter(subject=subject)
        sg = {}
        for m in subj_marks:
            short_form, _ = get_grade_and_points(school, int(m.marks))
            sg[short_form] = sg.get(short_form, 0) + 1
            all_grade_letters.add(short_form)
        subject_grade_counts[subject.name] = sg

    grade_columns = sorted(all_grade_letters, reverse=True)

    subj_grade_data = [["SUBJECT"] + grade_columns]
    for subj in subjects:
        row = [subj.name]
        sg = subject_grade_counts.get(subj.name, {})
        for g in grade_columns:
            row.append(sg.get(g, 0))
        subj_grade_data.append(row)

    col_widths = [100] + [60] * len(grade_columns)
    subj_table = Table(subj_grade_data, colWidths=col_widths)
    subj_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(subj_table)

    # BUILD PDF
    # =====================================================
    doc.build(elements)

    return response


@login_required
def marksheet_center(request):
    
    school = request.user.school

    classes = Class.objects.filter(
        school=school
    )

    terms = Term.objects.filter(
        school=school
    )

    exams = Exam.objects.filter(
        school=school
    )

    subjects = Subject.objects.filter(
        school=school
    )

    selected_class = request.GET.get("class")
    selected_term = request.GET.get("term")
    selected_exam = request.GET.get("exam")
    selected_stream = request.GET.get("stream")

    students = []
    streams = []
    selected_stream_obj = None
    display_title = ""

    # =====================================================
    # GET STREAMS FOR SELECTED CLASS
    # =====================================================
    if selected_class:
        streams = Stream.objects.filter(
            class_group_id=selected_class
        ).order_by("name")
        
        if selected_stream:
            selected_stream_obj = get_object_or_404(
                Stream,
                id=selected_stream,
                class_group_id=selected_class
            )

    # =====================================================
    # LOAD STUDENTS + RESULTS
    # =====================================================
    if selected_class and selected_term:

        students = Student.objects.filter(
            school=school,
            current_class_id=selected_class
        ).prefetch_related(
            "studentmark_set"
        )
        
        # Filter by stream if selected
        if selected_stream_obj:
            students = students.filter(stream=selected_stream_obj)
            class_obj = get_object_or_404(Class, id=selected_class)
            display_title = f"{class_obj.name} {selected_stream_obj.name} - Marksheet"
        else:
            class_obj = get_object_or_404(Class, id=selected_class)
            display_title = f"{class_obj.name} - Marksheet"

        # ===============================================
        # PROCESS RESULTS
        # ===============================================
        for student in students:

            total_marks = 0
            total_points = 0
            subject_count = 0

            results = []

            for subject in subjects:

                mark_obj = StudentMark.objects.filter(
                    student=student,
                    subject=subject,
                    term_id=selected_term
                ).first()

                if mark_obj:

                    mark = int(mark_obj.marks)

                    total_marks += mark
                    total_points += mark_obj.points
                    subject_count += 1

                    results.append({
                        "subject": subject.name,
                        "marks": mark,
                        "grade": mark_obj.grade,
                        "points": mark_obj.points
                    })

                else:

                    results.append({
                        "subject": subject.name,
                        "marks": "-",
                        "grade": "-",
                        "points": "-"
                    })

            # ===========================================
            # AVERAGE
            # ===========================================
            average = 0

            if subject_count > 0:
                average = round(total_marks / subject_count)

            # ===========================================
            # FINAL GRADE USING YOUR GRADING POLICY
            # ===========================================
            grade_obj = GradingPolicy.objects.filter(
                school=school,
                min_score__lte=average,
                max_score__gte=average
            ).first()

            final_grade = "-"

            if grade_obj:
                final_grade = grade_obj.short_form

            # ===========================================
            # ATTACH TO STUDENT
            # ===========================================
            student.results = results
            student.total_marks = total_marks
            student.average_marks = average
            student.final_grade = final_grade
            student.total_points = total_points

        # ===============================================
        # RANKING
        # ===============================================
        ranked_students = sorted(
            students,
            key=lambda x: x.total_marks,
            reverse=True
        )

        rank = 1

        for student in ranked_students:
            student.rank = rank
            rank += 1

        students = ranked_students

    # =====================================================
    # RENDER PAGE
    # =====================================================
    return render(request, "exams/marksheet_center.html", {

        "classes": classes,
        "terms": terms,
        "exams": exams,
        "subjects": subjects,
        "streams": streams,

        "students": students,

        "selected_class": selected_class,
        "selected_term": selected_term,
        "selected_exam": selected_exam,
        "selected_stream": selected_stream,
        "selected_stream_obj": selected_stream_obj,
        "display_title": display_title,

    })
    
@login_required
def marks_hub(request):

    school = request.user.school

    # =====================================================
    # FILTER DATA
    # =====================================================
    classes = Class.objects.filter(
        school=school
    )

    subjects = Subject.objects.filter(
        school=school
    )

    terms = Term.objects.filter(
        school=school
    )

    exams = Exam.objects.filter(
        school=school
    )

    # =====================================================
    # SELECTED VALUES
    # =====================================================
    selected_class = request.GET.get("class")
    selected_term = request.GET.get("term")
    selected_exam = request.GET.get("exam")

    students = []
    subject_headers = []

    # =====================================================
    # LOAD RESULTS
    # =====================================================
    if selected_class and selected_term:

        students = Student.objects.filter(
            school=school,
            current_class_id=selected_class
        )

        subject_headers = Subject.objects.filter(
            school=school
        )

        processed_students = []

        for student in students:

            marks_data = []

            total_marks = 0
            total_points = 0
            subject_count = 0

            # =============================================
            # SUBJECT LOOP
            # =============================================
            for subject in subject_headers:

                mark_obj = StudentMark.objects.filter(
                    student=student,
                    subject=subject,
                    term_id=selected_term
                ).first()

                if mark_obj:

                    mark = int(mark_obj.marks)

                    marks_data.append({
                        "subject": subject.name,
                        "marks": mark,
                        "grade": mark_obj.grade,
                        "points": mark_obj.points
                    })

                    total_marks += mark
                    total_points += mark_obj.points
                    subject_count += 1

                else:

                    marks_data.append({
                        "subject": subject.name,
                        "marks": "-",
                        "grade": "-",
                        "points": "-"
                    })

            # =============================================
            # AVERAGE
            # =============================================
            average = 0

            if subject_count > 0:
                average = round(total_marks / subject_count)

            # =============================================
            # FINAL GRADE
            # =============================================
            grade_obj = GradingPolicy.objects.filter(
                school=school,
                min_score__lte=average,
                max_score__gte=average
            ).first()

            final_grade = "-"

            if grade_obj:
                final_grade = grade_obj.grade_letter

            processed_students.append({

                "student": student,

                "marks_data": marks_data,

                "total_marks": total_marks,

                "average": average,

                "grade": final_grade,

                "points": total_points,

            })

        # =================================================
        # RANKING
        # =================================================
        processed_students = sorted(
            processed_students,
            key=lambda x: x["total_marks"],
            reverse=True
        )

        rank = 1

        for item in processed_students:
            item["rank"] = rank
            rank += 1

        students = processed_students

    # =====================================================
    # RENDER
    # =====================================================
    return render(request, "exams/marks_hub.html", {

        "classes": classes,
        "subjects": subjects,
        "terms": terms,
        "exams": exams,

        "students": students,
        "subject_headers": subject_headers,

        "selected_class": selected_class,
        "selected_term": selected_term,
        "selected_exam": selected_exam,
    })

# =====================================================
# IMPORT API VIEWS
# =====================================================
from .views_class_api_patch import class_details_json  
# =========================================================
# MANAGE GRADING POLICIES
# =========================================================

@login_required
def manage_grading(request):

    school = request.user.school

    gradings = GradingPolicy.objects.filter(
        school=school
    ).order_by("-min_score")

    return render(
        request,
        "dos/manage_grading.html",
        {
            "gradings": gradings
        }
    )


# =========================================================
# ADD GRADING POLICY
# =========================================================

@login_required
def add_grading_policy(request):

    school = request.user.school

    if request.method == "POST":

        GradingPolicy.objects.create(
            school=school,
            grade_letter=request.POST.get("grade_letter"),
            short_form=request.POST.get("short_form"),
            min_score=request.POST.get("min_score"),
            max_score=request.POST.get("max_score"),
            points=request.POST.get("points"),
            remarks=request.POST.get("remarks")
        )

        messages.success(
            request,
            "Grading policy added successfully."
        )

    return redirect("manage_grading")


# =========================================================
# EDIT GRADING POLICY
# =========================================================

@login_required
def edit_grading_policy(request, grading_id):

    school = request.user.school

    grading = get_object_or_404(
        GradingPolicy,
        id=grading_id,
        school=school
    )

    if request.method == "POST":

        grading.grade_letter = request.POST.get("grade_letter")
        grading.short_form = request.POST.get("short_form")
        grading.min_score = request.POST.get("min_score")
        grading.max_score = request.POST.get("max_score")
        grading.points = request.POST.get("points")
        grading.remarks = request.POST.get("remarks")

        grading.save()

        messages.success(
            request,
            "Grading policy updated successfully."
        )

        return redirect("manage_grading")

    return render(
        request,
        "dos/edit_grading.html",
        {
            "grading": grading
        }
    )


# =========================================================
# DELETE GRADING POLICY
# =========================================================

@login_required
def delete_grading_policy(request, grading_id):

    school = request.user.school

    grading = get_object_or_404(
        GradingPolicy,
        id=grading_id,
        school=school
    )

    grading.delete()

    messages.success(
        request,
        "Grading policy deleted successfully."
    )

    return redirect("manage_grading")              
                                  
import qrcode, base64
from io import BytesIO


import matplotlib.pyplot as plt

def generate_progress_chart(scores):
    fig, ax = plt.subplots()
    ax.plot(range(1, len(scores)+1), scores, marker='o')
    ax.set_title("Performance Progress")
    ax.set_xlabel("Exam")
    ax.set_ylabel("Score")
    buffer = BytesIO()
    plt.savefig(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode()

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch

# helper: grade + points + remarks
def get_grade_points_and_remarks(school, mark):
    grading = GradingPolicy.objects.filter(
        school=school,
        min_score__lte=mark,
        max_score__gte=mark
    ).first()
    if grading:
        return grading.short_form or grading.grade_letter, grading.points, grading.remarks
    return "-", 0, ""

# helper: QR image
def generate_qr_image(data):
    from io import BytesIO
    try:
        import qrcode
        qr = qrcode.QRCode(box_size=3, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return RLImage(buffer, width=60, height=60)
    except Exception:
        # Fallback: return a small blank image if qrcode is unavailable
        try:
            from PIL import Image as PILImage, ImageDraw
            img = PILImage.new("RGB", (60, 60), color="white")
            draw = ImageDraw.Draw(img)
            draw.rectangle([0, 0, 59, 59], outline="black")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            return RLImage(buffer, width=60, height=60)
        except Exception:
            # Last resort: return None
            return None
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle,
    Spacer, PageBreak
)

@login_required
def export_class_report(request, class_id, term_id, exam_id):

    school = request.user.school

    class_obj = get_object_or_404(Class, id=class_id, school=school)
    term_obj = get_object_or_404(Term, id=term_id, school=school)
    exam_obj = get_object_or_404(Exam, id=exam_id, school=school)

    stream_id = request.GET.get("stream_id")
    selected_stream = None
    if stream_id:
        selected_stream = get_object_or_404(Stream, id=stream_id, class_group=class_obj)

    student_query = Student.objects.filter(
        school=school,
        current_class_id=class_id
    )
    if selected_stream:
        student_query = student_query.filter(stream=selected_stream)

    students = student_query.order_by("name")

    subjects = Subject.objects.filter(
        school=school
    ).order_by("name")

    # Get class teacher and principal info
    class_teacher_name = "Class Teacher"
    class_teacher_phone = ""
    class_teacher_assignment = None

    if selected_stream:
        class_teacher_assignment = ClassTeacherAssignment.objects.filter(
            class_obj=class_obj,
            stream=selected_stream
        ).select_related("teacher").first()
    else:
        class_teacher_assignment = ClassTeacherAssignment.objects.filter(
            class_obj=class_obj
        ).select_related("teacher").first()

    if class_teacher_assignment and class_teacher_assignment.teacher:
        class_teacher_name = class_teacher_assignment.teacher.name
        class_teacher_phone = class_teacher_assignment.teacher.phone or ""

    principal = school.principals.first()
    principal_name = principal.name if principal else "Principal"
    principal_phone = principal.phone if principal else ""

    # Get previous exam for subject positioning
    previous_exam = Exam.objects.filter(
        school=school,
        term=term_obj
    ).exclude(id=exam_id).order_by('-created_at').first()

    # Extract year from term name if possible
    year = "2024"
    try:
        year = term_obj.name.split()[-1] if term_obj.name else "2024"
    except:
        pass

    response = HttpResponse(content_type="application/pdf")
    
    # Enhanced filename: Grade{grade}_Report_forms_{term}_{year}
    filename = f"Grade_Report_forms_{term_obj.name}_{year}.pdf"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        leftMargin=20,
        rightMargin=20,
        topMargin=20,
        bottomMargin=20
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportHeader", fontSize=12, leading=16, spaceAfter=6))
    styles.add(ParagraphStyle(name="ReportInfo", fontSize=9, leading=12, spaceAfter=4))
    styles.add(ParagraphStyle(name="ReportSmall", fontSize=8, leading=10))
    elements = []

    # =========================
    # RANKING & POSITIONING
    # =========================
    totals = {}

    for student in students:
        total = 0
        for subject in subjects:
            m = StudentMark.objects.filter(
                student=student,
                subject=subject,
                term=term_obj
            ).first()
            if m:
                total += float(m.marks)

        totals[student.id] = total

    ranking = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    ranks = {sid: i + 1 for i, (sid, _) in enumerate(ranking)}

# ======================
# SUBJECT POSITIONS (current exam only)
# ======================
    subject_positions = {}

    for student in students:
        subject_positions[student.id] = {}
        for subject in subjects:
        # Get all marks for this subject in the current term
         marks_qs = StudentMark.objects.filter(
            subject=subject,
            term=term_obj
        ).order_by('-marks')

        # Build ranking list
         ranking = list(marks_qs)
         student_mark = marks_qs.filter(student=student).first()

         if student_mark:
            # Find position in ranking
            pos = next((i + 1 for i, m in enumerate(ranking) if m.student_id == student.id), None)
            subject_positions[student.id][subject.id] = pos
        else:
            subject_positions[student.id][subject.id] = None

    # =========================
    # REPORT PER STUDENT
    # =========================
    for idx, student in enumerate(students):

        # ================= HEADER =================
        logo = ""
        if school.logo:
            try:
                logo = RLImage(school.logo.path, 0.8*inch, 0.8*inch)
            except:
                logo = ""

        stream_display = f" | Stream: {student.stream.name}" if student.stream else ""
        dorm_display = f" | Dorm: {student.dormitory.name}" if student.dormitory else ""

        header_text = f"""
        <b>{school.name}</b><br/>
        {school.address or ""}<br/>
        {school.phone or ""} | {school.email or ""}<br/><br/>
        <b>ACADEMIC REPORT FORM</b><br/>
        Class: {class_obj.name}{stream_display} | Term: {term_obj.name} | Exam: {exam_obj.name}
        """

        header = Table(
            [[logo, Paragraph(header_text, styles["Normal"])]],
            colWidths=[70, 440]
        )

        header.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, -1), 1, colors.black),
        ]))

        elements.append(header)
        elements.append(Spacer(1, 8))

        # ================= STUDENT INFO =================
        overall_pos = ranks.get(student.id, '-')
        info = f"""
        <b>Student Name:</b> {student.name} &nbsp;&nbsp;
        <b>Adm No:</b> {student.admission_number} &nbsp;&nbsp;
        <b>Position:</b> {overall_pos}/{len(students)}{dorm_display}
        """

        elements.append(Paragraph(info, styles["ReportInfo"]))
        elements.append(Spacer(1, 8))

        # ================= MARKS TABLE WITH TEACHER & POSITIONING =================
        table_data = [["Subject", "Marks", "Grade", "Points", "Teacher", "Pos", "Comments"]]

        total_marks = 0
        total_points = 0

        for subject in subjects:

            mark = StudentMark.objects.filter(
                student=student,
                subject=subject,
                term=term_obj
            ).first()

            # Get subject teacher
            teacher_name = "—"
            subject_teacher = TeacherSubjectAssignment.objects.filter(
                class_obj=class_obj,
                subject=subject,
                stream=student.stream if student.stream else None
            ).select_related("teacher").first()
            
            if subject_teacher:
                teacher_name = subject_teacher.teacher.name[:15]  # Abbreviate for space

            # Subject positioning indicator
            subject_position = (subject_positions.get(subject.id, {}).get(student.id, "-")
            if subject_positions.get(subject.id) else "-"
            )
            if mark:
                m = int(round(mark.marks))
                grade, points, remarks = get_grade_points_and_remarks(school, m)

                total_marks += m
                total_points += points

                table_data.append([
                Paragraph(subject.name, styles["ReportSmall"]),
                m,
                grade,
                    points,
                    Paragraph(teacher_name, styles["ReportSmall"]),
                    subject_position,
                    Paragraph(remarks, styles["ReportSmall"])
                ])
            else:
                table_data.append([
                    Paragraph(subject.name, styles["ReportSmall"]),
                    "-", "-", "-",
                    Paragraph(teacher_name, styles["ReportSmall"]),
                    subject_position,
                    "-"
                ])

        # ================= TABLE STYLE =================
        table = Table(
            table_data,
            colWidths=[130, 45, 40, 40, 80, 30, 90]
        )

        table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 1), (4, -1), "CENTER"),
            ("ALIGN", (5, 1), (5, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 10))

        # ================= TOTALS ANALYSIS =================
        avg = total_marks / len(subjects) if subjects else 0
        avg_display = int(round(avg))
        final_grade, _, final_remarks = get_grade_points_and_remarks(school, avg_display)

        totals_text = (
            f"<b>Total Marks:</b> {int(total_marks)} | "
            f"<b>Average:</b> {avg_display} | "
            f"<b>Total Points:</b> {int(total_points)} | "
            f"<b>Grade:</b> {final_grade}"
        )

        elements.append(Paragraph(totals_text, styles["ReportHeader"]))
        elements.append(Spacer(1, 8))

        # ================= SIGNATURES & COMMENTS SECTION =================
        teacher_block = []
        teacher_block.append(Paragraph(f"<b>Class Teacher: {class_teacher_name}</b>", styles["ReportInfo"]))
        if class_teacher_phone:
            teacher_block.append(Paragraph(f"Phone: {class_teacher_phone}", styles["ReportSmall"]))
            remarks = final_remarks if final_remarks else "—"
            teacher_block.append(Paragraph(f"Comments: {remarks}", styles["ReportSmall"]))
        teacher_block.append(Paragraph("Signature: ________________________", styles["ReportSmall"]))
        teacher_block.append(Spacer(1, 4))
        
        teacher_block.append(Paragraph(f"<b>Principal: {principal_name}</b>", styles["ReportInfo"]))
        if principal_phone:
            teacher_block.append(Paragraph(f"Phone: {principal_phone}", styles["ReportSmall"]))
            remarks = final_remarks if final_remarks else "—"
            teacher_block.append(Paragraph(f"Comments: {remarks}", styles["ReportSmall"]))
        teacher_block.append(Paragraph("Signature: ________________________", styles["ReportSmall"]))
        teacher_block.append(Spacer(1, 6))

        # QR code for student
        try:
            qr_img = generate_qr_image(f"{school.name} - {student.admission_number}")
        except Exception:
            qr_img = None

        # Progress graph
        try:
            scores = []
            for subject in subjects:
                m = StudentMark.objects.filter(student=student, subject=subject, term=term_obj).first()
                scores.append(int(round(m.marks))) if m else scores.append(0)

            b64 = generate_progress_chart(scores)
            import base64
            from io import BytesIO
            img_bytes = base64.b64decode(b64)
            buf = BytesIO(img_bytes)
            progress_img = RLImage(buf, width=200, height=100)
        except Exception:
            progress_img = None

        # Build side-by-side layout
        left_flowables = teacher_block
        if qr_img:
            left_flowables.append(Spacer(1, 4))
            left_flowables.append(qr_img)

        right_flowables = []
        if progress_img:
            right_flowables.append(progress_img)
        else:
            right_flowables.append(Paragraph("Progress chart unavailable", styles["ReportSmall"]))

        columns_table = Table([[left_flowables, right_flowables]], colWidths=[270, 230])
        columns_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.0, colors.white),
        ]))

        elements.append(columns_table)
        elements.append(Spacer(1, 8))

        # ================= FOOTER =================
        elements.append(Paragraph(
            "Powered by Brainet Analytics | Grade Report Forms",
            styles["Normal"]
        ))

        # PAGE BREAK
        if idx < len(students) - 1:
            elements.append(PageBreak())

    doc.build(elements)

    return response

@login_required
def clear_notifications(request):
    qs = Notification.objects.filter(recipient=request.user)
    deleted_info = qs.delete()
    deleted_count = deleted_info[0] if isinstance(deleted_info, (list, tuple)) else 0

    try:
        from django.contrib import messages
        messages.success(request, f"Cleared {deleted_count} notifications.")
    except Exception:
        pass

    # If this was an AJAX/API call, return JSON; otherwise redirect back to dashboard
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        from django.http import JsonResponse
        return JsonResponse({"deleted": deleted_count})

    return redirect("dos_dashboard")  # adjust to your dashboard view name

from django.contrib import messages

def add_term(request):
    if request.method == "POST":
        name = request.POST.get("name")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        school = request.user.school

        Term.objects.create(
            name=name,
            start_date=start_date,
            end_date=end_date,
            school=school
        )

        messages.success(request, "Term added successfully ✅")
        return redirect("manage_terms")

    return render(request, "schools/add_term.html")


@login_required
def edit_term(request, term_id):
    school = request.user.school
    term = get_object_or_404(Term, id=term_id, school=school)

    if request.method == "POST":
        term.name = request.POST.get("name")
        term.start_date = request.POST.get("start_date")
        term.end_date = request.POST.get("end_date")
        term.save()

        messages.success(request, "Term updated successfully ✏️")
        return redirect("manage_terms")

    return render(request, "schools/edit_term.html", {"term": term})


@login_required
def delete_term(request, term_id):
    school = request.user.school
    term = get_object_or_404(Term, id=term_id, school=school)

    if request.method == "POST":
        term.delete()
        messages.success(request, "Term deleted successfully 🗑")
        return redirect("manage_terms")

    return render(request, "schools/delete_term.html", {"term": term})


# =========================================================
# STUDENT PROMOTION
# =========================================================

@login_required
def promotion_center(request):
    """Main promotion center for managing student promotions"""
    school = request.user.school
    
    classes = Class.objects.filter(school=school)
    students = Student.objects.filter(school=school, status='active')
    
    context = {
        'classes': classes,
        'students': students,
        'total_students': students.count(),
    }
    return render(request, "schools/promotion_center.html", context)


@login_required
def promote_class_view(request, class_id):
    """Promote all students in a class to the next level"""
    from .promotion_service import PromotionService
    
    school = request.user.school
    class_obj = get_object_or_404(Class, id=class_id, school=school)
    
    if request.method == "POST":
        stats = PromotionService.promote_class(class_obj, promoted_by=request.user)
        
        messages.success(
            request,
            f"Promotion complete! Promoted: {stats['promoted']}, "
            f"Graduated: {stats['graduated']}, Failed: {stats['failed']}"
        )
        return redirect("promotion_center")
    
    students = Student.objects.filter(current_class=class_obj, status='active')
    
    context = {
        'class': class_obj,
        'students': students,
    }
    return render(request, "schools/promote_class_confirm.html", context)


@login_required
def promote_student_view(request, student_id):
    """Promote or handle individual student"""
    from .promotion_service import PromotionService
    
    school = request.user.school
    student = get_object_or_404(Student, id=student_id, school=school)
    
    if request.method == "POST":
        action = request.POST.get("action", "promote")
        remarks = request.POST.get("remarks", "")
        
        if action == "promote":
            next_class, next_stream = PromotionService.get_next_class(
                student.current_class, 
                student.stream
            )
            promotion = PromotionService.promote_student(
                student,
                next_class,
                next_stream,
                promoted_by=request.user,
                remarks=remarks
            )
            messages.success(
                request,
                f"{student.name} promoted to {next_class.name if next_class else 'Graduated'}"
            )
        
        elif action == "repeat":
            PromotionService.repeat_student(
                student,
                repeated_by=request.user,
                remarks=remarks
            )
            messages.success(request, f"{student.name} will repeat the year")
        
        elif action == "drop":
            PromotionService.drop_student(
                student,
                dropped_by=request.user,
                remarks=remarks
            )
            messages.success(request, f"{student.name} has been dropped from school")
        
        return redirect("promotion_center")
    
    next_class, next_stream = PromotionService.get_next_class(
        student.current_class,
        student.stream
    )
    
    context = {
        'student': student,
        'next_class': next_class,
        'next_stream': next_stream,
    }
    return render(request, "schools/promote_student.html", context)


@login_required
def promote_school_view(request):
    """Promote all students in the school"""
    from .promotion_service import PromotionService
    
    school = request.user.school
    
    if request.method == "POST":
        stats = PromotionService.promote_school(school, promoted_by=request.user)
        
        messages.success(
            request,
            f"School-wide promotion complete! Total: {stats['total_students']}, "
            f"Promoted: {stats['promoted']}, Graduated: {stats['graduated']}, "
            f"Failed: {stats['failed']}"
        )
        return redirect("promotion_center")
    
    classes = Class.objects.filter(school=school)
    students_count = Student.objects.filter(school=school, status='active').count()
    
    context = {
        'classes': classes,
        'students_count': students_count,
    }
    return render(request, "schools/promote_school_confirm.html", context)


@login_required
def promotion_history(request):
    """View promotion history"""
    school = request.user.school
    promotions = StudentPromotion.objects.filter(school=school).select_related(
        'student', 'from_class', 'to_class', 'promoted_by'
    )
    
    # Filtering
    student_name = request.GET.get("student")
    status_filter = request.GET.get("status")
    
    if student_name:
        promotions = promotions.filter(student__name__icontains=student_name)
    
    if status_filter:
        promotions = promotions.filter(status=status_filter)
    
    context = {
        'promotions': promotions,
        'student_name': student_name,
        'status_filter': status_filter,
        'status_choices': StudentPromotion.PROMOTION_STATUS,
    }
    return render(request, "schools/promotion_history.html", context)


# =========================================================
# MANUAL USER VERIFICATION - Admin Helper
# =========================================================
@login_required
@superuser_required
def manual_verify_user(request, user_id):
    """
    Manually verify a user's email account.
    Helps bypass failed verification attempts.
    Only accessible to superusers.
    """
    user = get_object_or_404(User, id=user_id)
    
    if request.method == "POST":
        try:
            user.mark_email_verified()
            messages.success(
                request,
                f"✅ User {user.email} has been manually verified!"
            )
            return redirect("superuser_dashboard")
        except Exception as e:
            messages.error(
                request,
                f"❌ Error verifying user: {str(e)}"
            )
            return redirect("superuser_dashboard")
    
    context = {
        'user': user,
        'is_verified': user.email_verified,
    }
    return render(request, "schools/manual_verify_user.html", context)


# =========================================================
# GET ONLINE CLASS MEETING LINK - With Authorization
# =========================================================
@login_required
def get_online_class_meeting_link(request, online_class_id):
    """
    Fetch the meeting link for an online class.
    ONLY returns the link if student is in the target class/stream.
    
    This prevents unauthorized students from accessing meeting links.
    """
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return JsonResponse(
            {"error": "Student profile not found"},
            status=403
        )
    
    online_class = get_object_or_404(OnlineClass, id=online_class_id)
    
    # =========================================
    # VERIFY STUDENT IS IN TARGET CLASS
    # =========================================
    if student.current_class_id != online_class.class_obj_id:
        return JsonResponse(
            {"error": "You are not enrolled in this class"},
            status=403
        )
    
    # =========================================
    # VERIFY STUDENT IS IN TARGET STREAM (if stream-specific)
    # =========================================
    if online_class.stream:
        if not student.stream or student.stream_id != online_class.stream_id:
            return JsonResponse(
                {"error": "You are not in the stream for this class"},
                status=403
            )
    
    # =========================================
    # RETURN MEETING LINK (Authorized)
    # =========================================
    from django.http import JsonResponse
    return JsonResponse({
        "success": True,
        "meeting_link": online_class.meeting_link,
        "topic": online_class.topic,
        "teacher": online_class.teacher.name,
    })


# =========================================================
# STUDENT JOIN ONLINE CLASS
# =========================================================
@login_required
def student_join_online_class(request, online_class_id):
    """
    Allow a student to join an online class.
    Creates/updates OnlineClassParticipant record and redirects to meeting link.
    
    TARGETING LOGIC:
    - Student MUST be in the online_class.class_obj
    - IF online_class.stream is set: student MUST be in that stream
    - IF online_class.stream is NULL: all students in class can join
    """
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "❌ Student profile not found.")
        return redirect("student_dashboard")
    
    online_class = get_object_or_404(OnlineClass, id=online_class_id)
    
    # =========================================
    # VERIFY STUDENT IS IN TARGET CLASS
    # =========================================
    if student.current_class_id != online_class.class_obj_id:
        messages.error(
            request,
            f"❌ You are not in {online_class.class_obj.name}. This class is only for that class."
        )
        return redirect("student_dashboard")
    
    # =========================================
    # VERIFY STUDENT IS IN TARGET STREAM (if stream-specific)
    # =========================================
    if online_class.stream:
        if not student.stream or student.stream_id != online_class.stream_id:
            messages.error(
                request,
                f"❌ You are not in {online_class.stream.name}. This class is only for that stream."
            )
            return redirect("student_dashboard")
    
    # =========================================
    # CREATE/UPDATE PARTICIPANT RECORD
    # =========================================
    try:
        participant, created = OnlineClassParticipant.objects.get_or_create(
            online_class=online_class,
            student=student
        )
        
        # Mark as joined
        participant.status = "joined"
        participant.save()
        
        action = "successfully joined" if created else "already joined"
        messages.success(
            request,
            f"✅ You have {action} '{online_class.topic}'! Redirecting to meeting..."
        )
        
        # =========================================
        # REDIRECT TO MEETING LINK (Authorized Access Only)
        # =========================================
        if online_class.meeting_link:
            return redirect(online_class.meeting_link)
        else:
            messages.warning(
                request,
                "⚠️ No meeting link available yet. Please contact your teacher."
            )
            return redirect("student_dashboard")
            
    except Exception as e:
        messages.error(
            request,
            f"❌ Error joining class: {str(e)}"
        )
        return redirect("student_dashboard")


# =========================================================
# STUDENT ONLINE CLASS ACTION (For other interactions)
# =========================================================
@login_required
def student_online_class_action(request, online_class_id):
    """
    Handle student actions on online classes (view details, record attempt, etc)
    
    TARGETING LOGIC:
    - Validates student is in the target class
    - Validates student is in target stream (if stream-specific)
    - Does NOT expose meeting link directly
    """
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect("student_dashboard")
    
    online_class = get_object_or_404(OnlineClass, id=online_class_id)
    
    # =========================================
    # VERIFY STUDENT CAN ACCESS THIS CLASS
    # =========================================
    if student.current_class_id != online_class.class_obj_id:
        messages.error(request, "❌ You don't have access to this class.")
        return redirect("student_dashboard")
    
    if online_class.stream and (not student.stream or student.stream_id != online_class.stream_id):
        messages.error(request, "❌ You don't have access to this stream's class.")
        return redirect("student_dashboard")
    
    # Get or create participant record
    participant, _ = OnlineClassParticipant.objects.get_or_create(
        online_class=online_class,
        student=student
    )
    
    action = request.GET.get("action", "view")
    
    if action == "view":
        # Show details WITHOUT the meeting link
        context = {
            'online_class': online_class,
            'participant': participant,
            'meeting_link': None,  # Don't expose link here
        }
        return render(request, "students/online_class_detail.html", context)
    
    elif action == "failed":
        # Mark as failed attempt
        participant.status = "failed"
        participant.save()
        messages.warning(request, "Failed join attempt recorded. Please try again or contact your teacher.")
        return redirect("student_dashboard")
    
    else:
        return redirect("student_dashboard")


# =========================================================
# MANUAL JOIN ONLINE CLASS - Admin Helper
# =========================================================
@login_required
@superuser_required
def manual_join_online_class(request, online_class_id, student_id):
    """
    Manually add a student to an online class and mark them as joined.
    Helps bypass failed join attempts.
    Only accessible to superusers.
    """
    online_class = get_object_or_404(OnlineClass, id=online_class_id)
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == "POST":
        try:
            participant, created = OnlineClassParticipant.objects.get_or_create(
                online_class=online_class,
                student=student
            )
            
            # Mark as joined
            participant.status = "joined"
            participant.save()
            
            action = "joined" if created else "updated to joined"
            messages.success(
                request,
                f"✅ {student.name} has been manually {action} the online class '{online_class.topic}'!"
            )
            return redirect("superuser_dashboard")
        except Exception as e:
            messages.error(
                request,
                f"❌ Error adding student to class: {str(e)}"
            )
            return redirect("superuser_dashboard")
    
    context = {
        'online_class': online_class,
        'student': student,
    }
    return render(request, "schools/manual_join_online_class.html", context)