import datetime
from datetime import timedelta
import email
import re
from urllib import request
from django.utils import timezone

from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, get_user_model, login
from django.db import transaction
from django.urls import reverse
from .models import DOSMessage, DOSQuery, Notification, School, DirectorOfStudies, Dormitory, Term, Class, Subject, GradingPolicy, StudentMark, StudentPromotion, SchoolNotice
from django.db import IntegrityError
from students.models import Student
from schools.models import School, Dormitory, DirectorOfStudies, Term
from schools.models import Class, Subject,VoucherRequest
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

@login_required
def request_voucher(request):

    school = request.user.school

    if request.method == "POST":

        VoucherRequest.objects.create(

            school=school,

            requested_by=request.user,

            student_count=request.POST["student_count"],

            term_id=request.POST["term"],

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
        "terms": terms
    }

    return render(
        request,
        "dashboards/request_voucher.html",
        context
    )

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
    # CONTEXT
    # ----------------------------
    # include pending license renewals so superusers can see reactivation requests
    from .models import LicenseRenewal
    pending_renewals = LicenseRenewal.objects.filter(status="pending").select_related("school", "requested_by").order_by("-requested_at")

    context = {

        "schools": schools,

        "active_schools": active_schools,

        "approved_vouchers": approved_vouchers,

        "pending_vouchers": pending_vouchers,

        "vouchers": vouchers,

        "queries": queries,

        "unread_queries": unread_queries,
        "pending_renewals": pending_renewals,
        "pending_renewals_count": pending_renewals.count(),
    }

    return render(
        request,
        "dashboards/superuser.html",
        context
    )
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
    return render(request, "dashboards/landing.html")

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

    return render(
        request,
        "dos/classes.html",
        {
            "classes": classes
        }
    )
    
    
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
def view_class_students(request, class_id):
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
@login_required
def manage_students(request):
    school = request.user.school

    students = Student.objects.filter(school=school)

    return render(request, "dos/manage_students.html", {
        "students": students
    })
@login_required
def add_student(request):

    school = request.user.school

    if request.method == "POST":

        name = request.POST.get("name")
        admission_number = request.POST.get("admission_number")
        gender = request.POST.get("gender")
        class_id = request.POST.get("class_id")

        school_class = get_object_or_404(
            Class,
            id=class_id,
            school=school
        )

        # =========================
        # EMAIL LOGIN SYSTEM ONLY
        # =========================
        email = f"{admission_number}@{school.name.lower().replace(' ', '')}.school"

        # prevent duplicates
        if User.objects.filter(email=email).exists():
            messages.error(request, "Student already exists")
            return redirect("add_student")

        # =========================
        # CREATE USER (NO USERNAME!)
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
            current_class=school_class
        )

        messages.success(
            request,
            f"Student created successfully! Login: {email} / {admission_number}"
        )

        return redirect("manage_students")

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
        student.current_class = get_object_or_404(
            Class,
            id=request.POST.get("class_id"),
            school=school
        )
        student.save()

        messages.success(request, "Student updated successfully.")
        return redirect("manage_students")

    return render(request, "dos/edit_student.html", {
        "student": student
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
        class_assigned=current_class
    ).order_by("-created_at")

    # =========================
    # SUBMISSIONS
    # =========================
    submissions = Submission.objects.filter(
        student=student
    )

    # =========================
    # CONTEXT
    # =========================
    return render(request, "students/dashboard.html", {
        "student": student,
        "class": current_class,
        "subjects": subjects,
        "assignments": assignments,
        "submissions": submissions,
    })
@login_required
def add_dorm(request):
    school = request.user.school

    if request.method == "POST":
        Dormitory.objects.create(
            name=request.POST.get("name"),
            school=school
        )

    return redirect("manage_dorms")
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
import datetime

@login_required
def download_class_list_pdf(request, class_id):

    # =========================
    # GET CLASS
    # =========================
    class_obj = Class.objects.get(id=class_id)

    # =========================
    # GET STUDENTS
    # =========================
    students = Student.objects.filter(
        current_class=class_obj
    ).order_by("name")

    # =========================
    # FILE NAME
    # =========================
    year = datetime.datetime.now().year

    filename = f"{class_obj.name}_{year}.pdf"

    folder_path = os.path.join(
        settings.MEDIA_ROOT,
        "class_lists"
    )

    os.makedirs(folder_path, exist_ok=True)

    file_path = os.path.join(folder_path, filename)

    # =========================
    # PDF DOCUMENT
    # =========================
    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()

    elements = []

    # =========================
    # SCHOOL HEADER + LOGO
    # =========================
    logo_path = None

    if class_obj.school.logo:
        logo_path = class_obj.school.logo.path

    row = []

    # SCHOOL LOGO
    if logo_path and os.path.exists(logo_path):

        logo = Image(
            logo_path,
            width=70,
            height=70
        )

        row.append(logo)

    # SCHOOL DETAILS
    school_text = Paragraph(
        f"""
        <font size="18">
        <b>{class_obj.school.name}</b>
        </font>
        <br/><br/>

        <font size="14">
        <u><b>CLASS LIST: {class_obj.name}</b></u>
        </font>

        <br/><br/>

        Academic Year: {year}
        """,
        styles["Title"]
    )

    row.append(school_text)

    header_table = Table(
        [row],
        colWidths=[90, 400]
    )

    elements.append(header_table)

    elements.append(Spacer(1, 20))

    # =========================
    # STUDENT TABLE
    # =========================
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
        colWidths=[40, 250, 120, 80]
    )

    table.setStyle(TableStyle([

        # HEADER
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),

        # GRID
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),

        # FONT
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

        # PADDING
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
        ("TOPPADDING", (0, 0), (-1, 0), 10),

        # ALIGNMENT
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),

        # BODY BACKGROUND
        ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),

    ]))

    elements.append(table)

    elements.append(Spacer(1, 25))

    # =========================
    # SUMMARY FOOTER
    # =========================
    total_students = students.count()

    male_students = students.filter(
        gender__iexact="Male"
    ).count()

    female_students = students.filter(
        gender__iexact="Female"
    ).count()

    footer = Paragraph(
        f"""
        <b>Total Students:</b> {total_students}
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
        <b>Male:</b> {male_students}
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
        <b>Female:</b> {female_students}
        """,
        styles["Normal"]
    )

    elements.append(footer)

    elements.append(Spacer(1, 30))

    # =========================
    # SYSTEM FOOTER
    # =========================
    generated = Paragraph(
        f"""
        Generated by Brainet ERP System
        """,
        styles["Italic"]
    )

    elements.append(generated)

    # =========================
    # BUILD PDF
    # =========================
    doc.build(elements)

    # =========================
    # RETURN DOWNLOAD RESPONSE
    # =========================
    with open(file_path, "rb") as pdf:

        response = HttpResponse(
            pdf.read(),
            content_type="application/pdf"
        )

        response[
            "Content-Disposition"
        ] = f'attachment; filename="{filename}"'

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

        messages.success(
            request,
            f"{role.replace('_', ' ').title()} account created successfully."
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

            # CREATE USER
            user = User.objects.create_user(
            email=email,
            password=password,
            role="dos",
            school=school

            )

            # CREATE DOS PROFILE
            DirectorOfStudies.objects.create(
                user=user,
                school=school,
                name=name,
                email=email,
                phone=phone
            )

            messages.success(
                request,
                f"{name} registered successfully."
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

            # CREATE USER
            user = CustomUser.objects.create_user(
                email=email,
                password=password,
                role="principal",
                school=school
            )

            # CREATE PRINCIPAL PROFILE
            Principal.objects.create(
                user=user,
                school=school,
                name=name,
                email=email,
                phone=phone
            )

            messages.success(request, f"{name} registered successfully as Principal.")

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
    school.save()
    messages.success(request, "School activated successfully.")
    return redirect("view_school", school_id=school.id)
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

        School.objects.create(
            name=name,
            address=address,
            phone=phone,
            email=email,
            subscription_balance=subscription_balance,
            logo=logo,
        )

        messages.success(request, "School added successfully.")
        messages.warning(
            request,
            "New school accounts expire within 48 hours if not activated. Contact admin to activate."
        )

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

        School.objects.create(
            name=name,
            address=address,
            phone=phone,
            email=email,
        )

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

    students = []
    subjects = []
    report_rows = []

    if class_id and term_id:

        # =====================================
        # ALL STUDENTS IN CLASS
        # =====================================
        students = Student.objects.filter(
            school=school,
            current_class_id=class_id,
            status="active"
        ).order_by("name")

        # =====================================
        # ALL SUBJECTS
        # =====================================
        subjects = Subject.objects.filter(
            school=school
        ).order_by("name")

        # =====================================
        # BUILD MARKSHEET ROWS
        # =====================================
        for student in students:

            subject_results = []

            total_marks = 0
            total_subjects = 0

            for subject in subjects:

                mark = StudentMark.objects.filter(
                    student=student,
                    subject=subject,
                    term_id=term_id
                ).first()

                if mark:

                    marks_value = mark.marks
                    grade_value = mark.grade

                    total_marks += mark.marks
                    total_subjects += 1

                else:

                    marks_value = "-"
                    grade_value = "-"

                subject_results.append({
                    "subject": subject,
                    "marks": marks_value,
                    "grade": grade_value,
                })

            # =====================================
            # AVERAGE
            # =====================================
            average = 0

            if total_subjects > 0:
                average = round(total_marks / total_subjects, 2)

            report_rows.append({
                "student": student,
                "subjects": subject_results,
                "total": total_marks,
                "average": average,
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
        position = 1

        for row in report_rows:
            row["position"] = position
            position += 1

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

    subjects = Subject.objects.filter(
        school=school
    )

    students = Student.objects.filter(
        school=school,
        current_class_id=class_id
    )

    marks = StudentMark.objects.filter(
        student__current_class_id=class_id,
        term_id=term_id
    ).select_related(
        "student",
        "subject"
    )

    # =====================================================
    # RESPONSE
    # =====================================================
    response = HttpResponse(content_type="application/pdf")

    response["Content-Disposition"] = (
        'attachment; filename="marksheet.pdf"'
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
    class_info = Paragraph(
        f"<b>MARKSHEET:</b> {class_obj.name} | <b>TERM:</b> {term_obj.name} | <b>YEAR:</b> {date.today().year}",
        styles["Normal"]
    )
    elements.append(class_info)
    elements.append(Spacer(1, 15))

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
        header.append(subject.name.upper())

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

    students = []

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

        "students": students,

        "selected_class": selected_class,
        "selected_term": selected_term,
        "selected_exam": selected_exam,

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

    students = Student.objects.filter(
        school=school,
        current_class_id=class_id
    ).order_by("name")

    subjects = Subject.objects.filter(
        school=school
    ).order_by("name")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="report_{class_obj.name}.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        leftMargin=25,
        rightMargin=25,
        topMargin=25,
        bottomMargin=25
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportHeader", fontSize=12, leading=16, spaceAfter=6))
    styles.add(ParagraphStyle(name="ReportInfo", fontSize=9, leading=12, spaceAfter=4))
    styles.add(ParagraphStyle(name="ReportSmall", fontSize=8, leading=10))
    elements = []

    # =========================
    # RANKING
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

    # =========================
    # REPORT PER STUDENT
    # =========================
    for idx, student in enumerate(students):

        # ================= HEADER =================
        logo = ""
        if school.logo:
            try:
                logo = RLImage(school.logo.path, 1*inch, 1*inch)
            except:
                logo = ""

        header_text = f"""
        <b>{school.name}</b><br/>
        {school.address or ""}<br/>
        {school.phone or ""} | {school.email or ""}<br/><br/>
        <b>ACADEMIC REPORT</b><br/>
        Class: {class_obj.name} | Term: {term_obj.name} | Exam: {exam_obj.name}
        """

        header = Table(
            [[logo, Paragraph(header_text, styles["Normal"])]],
            colWidths=[80, 430]
        )

        header.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, -1), 1, colors.black),
        ]))

        elements.append(header)
        elements.append(Spacer(1, 10))

        # ================= STUDENT INFO =================
        info = f"""
        <b>Name:</b> {student.name} &nbsp;&nbsp;
        <b>Adm:</b> {student.admission_number} &nbsp;&nbsp;
        <b>Rank:</b> {ranks.get(student.id,'-')}/{len(students)}
        """

        elements.append(Paragraph(info, styles["ReportInfo"]))
        elements.append(Spacer(1, 10))

        # ================= MARKS TABLE =================
        table_data = [["Subject", "Marks", "Grade", "Points", "Remarks"]]

        total_marks = 0
        total_points = 0

        for subject in subjects:

            mark = StudentMark.objects.filter(
                student=student,
                subject=subject,
                term=term_obj
            ).first()

            if mark:
                m = int(round(mark.marks))
                grade, points, remarks = get_grade_points_and_remarks(school, m)

                total_marks += m
                total_points += points

                table_data.append([
                    Paragraph(subject.name, styles["ReportInfo"]),
                    m,
                    grade,
                    points,
                    Paragraph(remarks, styles["ReportSmall"])
                ])
            else:
                table_data.append([Paragraph(subject.name, styles["ReportInfo"]), "-", "-", "-", "-"])

        # ================= TABLE STYLE =================
        table = Table(
            table_data,
            colWidths=[180, 50, 50, 50, 185]
        )

        table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 1), (-2, -1), "CENTER"),
            ("ALIGN", (4, 1), (4, -1), "LEFT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 12))

        # ================= TOTALS ANALYSIS (TEXT) =================
        avg = total_marks / len(subjects) if subjects else 0
        avg_display = int(round(avg))
        final_grade, _, final_remarks = get_grade_points_and_remarks(school, avg_display)

        # Use simple paragraphs (no table) for totals and summary
        totals_text = (
            f"<b>Total Marks:</b> {int(total_marks)} &nbsp;&nbsp; "
            f"<b>Average:</b> {avg_display} &nbsp;&nbsp; "
            f"<b>Points:</b> {int(total_points)} &nbsp;&nbsp; "
            f"<b>Grade:</b> {final_grade}"
        )

        elements.append(Paragraph(totals_text, styles["ReportHeader"]))
        elements.append(Spacer(1, 10))

        # ================= SIGNATURES, COMMENTS, QR & PROGRESS GRAPH =================
        # Teacher / Principal area on the left, QR bottom-left; progress graph on the right

        # Teacher info (use placeholders if not available)
        class_teacher_name = getattr(class_obj, "teacher_name", None) or "Class Teacher"
        class_teacher_phone = getattr(class_obj, "teacher_phone", None) or ""

        teacher_block = []
        teacher_block.append(Paragraph(f"<b>Class Teacher:</b> {class_teacher_name}", styles["ReportInfo"]))
        if class_teacher_phone:
            teacher_block.append(Paragraph(f"<b>Phone:</b> {class_teacher_phone}", styles["ReportInfo"]))
        teacher_block.append(Spacer(1, 8))
        teacher_block.append(Paragraph("Sign: ____________________________", styles["ReportInfo"]))
        teacher_block.append(Paragraph(f"<b>Teacher Comment:</b> {final_remarks}", styles["ReportSmall"]))
        teacher_block.append(Spacer(1, 6))
        teacher_block.append(Spacer(1, 8))

        # Principal placeholder
        teacher_block.append(Paragraph("<b>Principal:</b>", styles["ReportInfo"]))
        teacher_block.append(Spacer(1, 8))
        teacher_block.append(Paragraph("Sign: ____________________________", styles["ReportInfo"]))

        # Teacher comments
        teacher_block.append(Spacer(1, 6))
        teacher_block.append(Paragraph(f"<b>Teacher Comment:</b> {final_remarks}", styles["ReportSmall"]))
        teacher_block.append(Spacer(1, 6))

        # QR code for student (bottom-left)
        try:
            qr_img = generate_qr_image(f"{school.name} - {student.admission_number}")
        except Exception:
            qr_img = None

        # Progress graph: plot marks per subject for this student in current exam
        try:
            scores = []
            for subject in subjects:
                m = StudentMark.objects.filter(student=student, subject=subject, term=term_obj).first()
                scores.append(int(round(m.marks))) if m else scores.append(0)

            # generate base64 png from helper
            b64 = generate_progress_chart(scores)
            import base64
            from io import BytesIO
            img_bytes = base64.b64decode(b64)
            buf = BytesIO(img_bytes)
            progress_img = RLImage(buf, width=220, height=110)
        except Exception:
            progress_img = None

        # Build left and right columns
        left_flowables = teacher_block
        if qr_img:
            left_flowables.append(Spacer(1, 6))
            left_flowables.append(qr_img)

        right_flowables = []
        if progress_img:
            right_flowables.append(progress_img)
        else:
            right_flowables.append(Paragraph("Progress graph unavailable", styles["ReportSmall"]))

        # Place side-by-side
        columns_table = Table([[left_flowables, right_flowables]], colWidths=[280, 250])
        columns_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.0, colors.white),
        ]))

        elements.append(columns_table)
        elements.append(Spacer(1, 12))

        # ================= FOOTER =================
        elements.append(Paragraph(
            "Powered by Brainet Analytics",
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

