import csv
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from assignments.models import Assignment, Submission
from classes.models import Class, Stream
from schools.models import Notification, Principal, Subject, SchoolNotice
from students.models import Student
from users.models import CustomUser
from .models import (
    Teacher,
    ClassTeacherAssignment,
    TeacherSubjectAssignment,
    OnlineClass,
    OnlineClassParticipant,
)


def _can_manage_teachers(request):
    return request.user.is_superuser or getattr(request.user, "role", "") == "principal"
def _resolve_class_stream(class_obj, stream_id=None):
    if stream_id:
        return get_object_or_404(Stream, id=stream_id, class_group=class_obj)
    
    stream = class_obj.streams.order_by("id").first()
    if stream:
        return stream

    return Stream.objects.create(class_group=class_obj, name=None)

def assign_teacher_class(request):
    if not _can_manage_teachers(request):
        messages.error(request, "Permission denied.")
        return redirect("manage_teachers")

    school = request.user.school

    if request.method == "POST":

        teacher_id = request.POST.get("teacher")
        class_id = request.POST.get("class")
        stream_id = request.POST.get("stream")

        teacher = get_object_or_404(Teacher, id=teacher_id, school=school)
        class_obj = get_object_or_404(Class, id=class_id, school=school)

        stream = _resolve_class_stream(class_obj, stream_id)

        # update or create assignment for the selected class+stream
        assignment, created = ClassTeacherAssignment.objects.update_or_create(
            class_obj=class_obj,
            stream=stream,
            defaults={
                'school': school,
                'teacher': teacher
            }
        )

        messages.success(request, "Class assigned successfully")

    return redirect("manage_teachers")
@login_required
def add_teacher(request):
    if not _can_manage_teachers(request):
        messages.error(request, "Permission denied.")
        return redirect("manage_teachers")

    school = request.user.school

    if request.method == "POST":

        name = request.POST.get("name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        phone = request.POST.get("phone")
        role = request.POST.get("role")

        # Prevent duplicates
        if CustomUser.objects.filter(email=email).exists():
            messages.error(
                request,
                "A user with this email already exists."
            )
            return redirect("add_teacher")

        try:

            # =========================
            # CREATE USER ACCOUNT
            # =========================
            user = CustomUser.objects.create_user(
                email=email,
                password=password,
                school=school,
                role="teacher",
                email_verified=False  # Must verify via code before full access
            )

            # =========================
            # CREATE TEACHER PROFILE
            # =========================
            teacher = Teacher.objects.create(
                user=user,
                school=school,
                name=name,
                email=email,
                phone=phone,
                role=role
            )

            # If a class was selected during creation, create a class assignment
            class_id = request.POST.get("assigned_class")
            if class_id:
                try:
                    class_obj = Class.objects.get(id=class_id, school=school)
                    ClassTeacherAssignment.objects.create(
                        school=school,
                        class_obj=class_obj,
                        stream=_resolve_class_stream(class_obj),
                        teacher=teacher
                    )
                except Exception:
                    pass

            # Send verification email
            from schools.views import send_user_verification_email
            send_user_verification_email(user, request=request, role_name='Teacher')

            messages.success(
                request,
                f"Teacher {name} added successfully. A verification email has been sent to {email}."
            )

            return redirect("manage_teachers")

        except Exception as e:

            messages.error(
                request,
                f"Error creating teacher: {str(e)}"
            )

            return redirect("add_teacher")

    return render(
        request,
        "teachers/add_teacher.html"
    )
    
@login_required
def teacher_dashboard(request):
    
    teacher = get_object_or_404(
        Teacher,
        user=request.user,
        school=request.user.school
    )

    school = teacher.school

    # =========================
    # CLASS ASSIGNMENTS (may be multiple, stream-aware)
    # =========================
    class_assignments = ClassTeacherAssignment.objects.filter(
        teacher=teacher
    ).select_related("class_obj", "stream")

    assigned_classes = []
    for ca in class_assignments:
        label = ca.class_obj.name
        if ca.stream:
            label = f"{label} — {ca.stream.name}"
        assigned_classes.append({
            "class_obj": ca.class_obj,
            "stream": ca.stream,
            "label": label,
        })

    # =========================
    # SUBJECTS (only those assigned to this teacher)
    # =========================
    subject_assignments = TeacherSubjectAssignment.objects.filter(
        teacher=teacher
    ).select_related("subject", "class_obj", "stream")

    subject_groups = {}
    for sa in subject_assignments:
        if sa.subject_id not in subject_groups:
            subject_groups[sa.subject_id] = {
                "subject": sa.subject,
                "classes": []
            }
        label = sa.class_obj.name
        if sa.stream:
            label = f"{label} — {sa.stream.name}"
        subject_groups[sa.subject_id]["classes"].append({
            "class_obj": sa.class_obj,
            "stream": sa.stream,
            "label": label,
        })

    subjects = list(subject_groups.values())

    # =========================
    # STUDENTS (SAFE) - prefer context of a single assignment if present
    # =========================
    if class_assignments.count() == 1:
        first = class_assignments.first()
        if first.stream:
            students = Student.objects.filter(
                school=school,
                current_class=first.class_obj,
                stream=first.stream
            )
        else:
            students = Student.objects.filter(
                school=school,
                current_class=first.class_obj
            )
    elif class_assignments.exists():
        class_ids = [ca.class_obj.id for ca in class_assignments]
        students = Student.objects.filter(
            school=school,
            current_class_id__in=class_ids
        )
    else:
        students = Student.objects.filter(school=school)

    # =========================
    # ASSIGNMENTS
    # =========================
    assignments = Assignment.objects.filter(
        teacher=teacher,
        school=school
    ).order_by("-created_at")

    # =========================
    # SUBMISSIONS
    # =========================
    submissions = Submission.objects.filter(
        assignment__teacher=teacher,
        school=school
    ).order_by("-submitted_at")

    # =========================
    # NOTIFICATIONS
    # =========================
    notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by("-created_at")[:10]

    unread_notifications = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()

    # =========================
    # SCHOOL NOTICES
    # =========================
    notices = SchoolNotice.objects.filter(school=school).filter(recipient_type__in=['teachers','all']).order_by('-created_at')

    # =========================
    # CONTEXT
    # =========================
    template_name = "dashboards/subject_teacher.html" if getattr(request.user, "role", "") == "subject_teacher" else "teachers/dashboard.html"

    online_classes = OnlineClass.objects.filter(
        teacher=teacher,
        school=school
    ).select_related("class_obj", "stream", "subject")

    return render(request, template_name, {
        "teacher": teacher,
        "assigned_classes": assigned_classes,
        "subjects": subjects,
        "subject_groups": subjects,
        "students": students,
        "assignments": assignments,
        "submissions": submissions,
        "notifications": notifications,
        "unread_notifications": unread_notifications,
        "notices": notices,
        "subjects_count": len(subjects),
        "students_count": students.count() if hasattr(students, 'count') else len(students),
        "assignments_count": assignments.count(),
        "pending_marks": submissions.filter(assignment__isnull=False).count() if hasattr(submissions, 'filter') else len(submissions),
        "online_classes": online_classes,
    })    


@login_required
def teacher_online_classes(request):
    teacher = get_object_or_404(
        Teacher,
        user=request.user,
        school=request.user.school
    )

    school = teacher.school

    assigned_class_ids = TeacherSubjectAssignment.objects.filter(
        teacher=teacher,
        school=school
    ).values_list("class_obj_id", flat=True).distinct()

    streams = Stream.objects.filter(
        id__in=TeacherSubjectAssignment.objects.filter(
            teacher=teacher,
            school=school,
            stream__isnull=False
        ).values_list("stream_id", flat=True).distinct()
    ).order_by("name")

    subjects = Subject.objects.filter(
        id__in=TeacherSubjectAssignment.objects.filter(
            teacher=teacher,
            school=school
        ).values_list("subject_id", flat=True).distinct(),
        school=school
    ).order_by("name")

    classes = Class.objects.filter(
        school=school,
        id__in=assigned_class_ids
    ).order_by("name")

    online_classes = OnlineClass.objects.filter(
        teacher=teacher,
        school=school
    ).select_related("class_obj", "stream", "subject").order_by("-start_time")

    if request.method == "POST":
        try:
            topic = request.POST.get("topic", "").strip()
            description = request.POST.get("description", "").strip()
            class_id = request.POST.get("class_id")
            stream_id = request.POST.get("stream_id")
            subject_id = request.POST.get("subject_id")
            meeting_link = request.POST.get("meeting_link", "").strip()
            tools = request.POST.get("tools", "Screen Share, Chat, Whiteboard").strip()
            start_time = parse_datetime(request.POST.get("start_time"))
            end_time = parse_datetime(request.POST.get("end_time"))
            duration_minutes = request.POST.get("duration_minutes")

            if not topic:
                messages.error(request, "Topic is required.")
                return redirect("teacher_online_classes")

            if not class_id:
                messages.error(request, "Class is required.")
                return redirect("teacher_online_classes")

            class_obj = get_object_or_404(Class, id=class_id, school=school)
            stream = None
            if stream_id:
                stream = get_object_or_404(Stream, id=stream_id, class_group__school=school)

            subject = None
            if subject_id:
                subject = get_object_or_404(Subject, id=subject_id, school=school)

            if not start_time or not end_time:
                messages.error(request, "Start time and end time are required.")
                return redirect("teacher_online_classes")

            if timezone.is_naive(start_time):
                start_time = timezone.make_aware(start_time, timezone.get_current_timezone())
            if timezone.is_naive(end_time):
                end_time = timezone.make_aware(end_time, timezone.get_current_timezone())

            if start_time >= end_time:
                messages.error(request, "End time must be after start time.")
                return redirect("teacher_online_classes")

            duration = None
            if duration_minutes:
                try:
                    duration = int(duration_minutes)
                except ValueError:
                    duration = None

            online_class = OnlineClass.objects.create(
                school=school,
                teacher=teacher,
                class_obj=class_obj,
                stream=stream,
                subject=subject,
                topic=topic,
                description=description,
                start_time=start_time,
                end_time=end_time,
                duration_minutes=duration,
                meeting_link=meeting_link or None,
                tools=tools,
            )

            students_for_class = Student.objects.filter(
                school=school,
                current_class=class_obj
            )
            if stream:
                students_for_class = students_for_class.filter(stream=stream)

            for student in students_for_class:
                OnlineClassParticipant.objects.get_or_create(
                    online_class=online_class,
                    student=student,
                )

            messages.success(request, "Online class scheduled successfully.")
            return redirect("teacher_online_classes")

        except Exception as e:
            messages.error(request, f"Could not schedule online class: {str(e)}")
            return redirect("teacher_online_classes")

    return render(request, "teachers/online_classes.html", {
        "teacher": teacher,
        "classes": classes,
        "streams": streams,
        "subjects": subjects,
        "online_classes": online_classes,
    })


@login_required
def teacher_online_class_detail(request, online_class_id):
    teacher = get_object_or_404(
        Teacher,
        user=request.user,
        school=request.user.school
    )

    online_class = get_object_or_404(
        OnlineClass,
        id=online_class_id,
        teacher=teacher,
        school=teacher.school
    )

    participants = OnlineClassParticipant.objects.filter(
        online_class=online_class
    ).select_related("student").order_by("-status", "joined_at")

    if request.method == "POST":
        if "board_save" in request.POST:
            board_notes = request.POST.get("board_notes", "").strip()
            board_attachment = request.FILES.get("board_attachment")
            online_class.board_notes = board_notes
            if board_attachment:
                online_class.board_attachment = board_attachment
            online_class.save()
            messages.success(request, "Class board updated successfully.")
            return redirect("teacher_online_class_detail", online_class_id=online_class.id)

        action = request.POST.get("action")
        participant_id = request.POST.get("participant_id")

        if participant_id:
            participant = get_object_or_404(
                OnlineClassParticipant,
                id=participant_id,
                online_class=online_class
            )

            if action == "toggle_mic":
                participant.mic_enabled = not participant.mic_enabled
                participant.save()
                messages.success(request, f"{participant.student.name}'s mic updated.")
            elif action == "mark_joined":
                participant.status = "joined"
                participant.joined_at = timezone.now()
                participant.save()
                messages.success(request, f"{participant.student.name} marked as joined.")
            elif action == "mark_failed":
                participant.status = "failed"
                participant.save()
                messages.success(request, f"{participant.student.name} marked as failed to join.")

        return redirect("teacher_online_class_detail", online_class_id=online_class.id)

    return render(request, "teachers/online_class_detail.html", {
        "teacher": teacher,
        "online_class": online_class,
        "participants": participants,
    })


@login_required
def edit_teacher(request, teacher_id):
    if not _can_manage_teachers(request):
        messages.error(request, "Permission denied.")
        return redirect("manage_teachers")

    teacher = get_object_or_404(Teacher, id=teacher_id, school=request.user.school)
    subjects = Subject.objects.filter(school=request.user.school)
    classes = Class.objects.filter(school=request.user.school)
    if request.method == "POST":
        email = request.POST.get("email", teacher.email).strip()
        teacher.name = request.POST["name"]
        teacher.phone = request.POST["phone"]
        teacher.role = request.POST["role"]

        if email and email != teacher.email:
            if CustomUser.objects.exclude(id=teacher.user_id).filter(email=email).exists():
                messages.error(request, "Another user already uses that email.")
                return redirect("edit_teacher", teacher_id=teacher.id)
            teacher.email = email
            if teacher.user:
                teacher.user.email = email
                teacher.user.email_verified = False
                teacher.user.save(update_fields=["email", "email_verified"])

            from schools.views import send_user_verification_email
            if not send_user_verification_email(teacher.user, request=request, role_name="Teacher"):
                from schools.views import _verification_contact_message
                messages.warning(request, f"Teacher details were updated, but the verification email could not be sent. {_verification_contact_message(request)}")

        class_id = request.POST.get("assigned_class")
        if class_id:
            class_obj = get_object_or_404(Class, id=class_id, school=request.user.school)
            # Remove any previous class assignments for this teacher and set the new one
            ClassTeacherAssignment.objects.filter(teacher=teacher).delete()
            ClassTeacherAssignment.objects.create(
                school=request.user.school,
                class_obj=class_obj,
                stream=_resolve_class_stream(class_obj),
                teacher=teacher
            )

        teacher.save()
        return redirect("manage_teachers")

    # Provide current assignments for the form
    class_assignment = ClassTeacherAssignment.objects.filter(teacher=teacher).select_related("class_obj", "stream").first()
    subject_assignments = TeacherSubjectAssignment.objects.filter(teacher=teacher).select_related("subject", "class_obj", "stream")

    return render(request, "schools/edit_teacher.html", {
        "teacher": teacher,
        "subjects": subjects,
        "classes": classes,
        "class_assignment": class_assignment,
        "subject_assignments": subject_assignments,
    })


@login_required
def delete_teacher(request, teacher_id):
    if not _can_manage_teachers(request):
        messages.error(request, "Permission denied.")
        return redirect("manage_teachers")

    teacher = get_object_or_404(Teacher, id=teacher_id, school=request.user.school)
    teacher.user.delete()  # delete login account too
    teacher.delete()
    return redirect("manage_teachers")
def export_teachers_pdf(request):
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="teachers.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # Title
    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, height - 50, "Teachers List")

    # Table header
    p.setFont("Helvetica-Bold", 12)
    y = height - 100
    p.drawString(50, y, "Name")
    p.drawString(200, y, "Phone")
    p.drawString(350, y, "School")

    # Table rows
    p.setFont("Helvetica", 12)
    y -= 30
    for teacher in Teacher.objects.all():
        p.drawString(50, y, teacher.name)
        p.drawString(200, y, teacher.phone)
        p.drawString(350, y, teacher.school.name)
        y -= 20
        if y < 50:  # new page if too long
            p.showPage()
            y = height - 50

    p.showPage()
    p.save()
    return response

@login_required
def manage_teachers(request):

    # =========================
    # GET SCHOOL SAFELY
    # =========================
    principal = get_object_or_404(Principal, user=request.user)
    school = principal.school

    # =========================
    # TEACHERS IN SCHOOL
    # =========================
    teachers = Teacher.objects.filter(school=school)

    # =========================
    # SUPPORT DATA (FOR ASSIGNING UI)
    # =========================
    classes = Class.objects.filter(school=school)
    subjects = Subject.objects.filter(school=school)

    # Build quick lookup maps for template
    class_assignments = ClassTeacherAssignment.objects.filter(teacher__in=teachers).select_related("teacher", "class_obj", "stream")
    teacher_class_map = {ca.teacher_id: ca for ca in class_assignments}

    subject_assignments = TeacherSubjectAssignment.objects.filter(teacher__in=teachers).select_related("teacher", "subject", "class_obj", "stream")
    teacher_subjects_map = {}
    for sa in subject_assignments:
        teacher_subjects_map.setdefault(sa.teacher_id, []).append(sa)

    # Attach to teacher instances for easier template access
    teachers = list(teachers)
    for t in teachers:
        t.assigned_class_assignment = teacher_class_map.get(t.id)
        t.subject_assignments = teacher_subjects_map.get(t.id, [])

    streams = Stream.objects.filter(class_group__school=school)

    return render(request, "schools/manage_teachers.html", {
        "school": school,
        "teachers": teachers,
        "classes": classes,
        "subjects": subjects,
        "streams": streams,
    })

def export_teachers(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="teachers.csv"'

    writer = csv.writer(response)
    writer.writerow(["Name", "Email", "Phone", "School", "Role"])

    for teacher in Teacher.objects.all():
        writer.writerow([
            teacher.name,
            teacher.email,
            teacher.phone,
            teacher.school.name,
            teacher.role()
        ])

    return response
def assign_teacher_subject(request):
    if not _can_manage_teachers(request):
        messages.error(request, "Permission denied.")
        return redirect("manage_teachers")
    
    school = request.user.school

    if request.method == "POST":

        teacher_id = request.POST.get("teacher")
        subject_id = request.POST.get("subject")

        from teachers.models import Teacher

        teacher = get_object_or_404(Teacher, id=teacher_id, school=school)
        subject = get_object_or_404(Subject, id=subject_id, school=school)

        class_id = request.POST.get("class")
        stream_id = request.POST.get("stream")

        if not class_id:
            messages.error(request, "Please select a class when assigning a subject.")
            return redirect("manage_teachers")

        class_obj = get_object_or_404(Class, id=class_id, school=school)
        stream = None
        if stream_id:
            stream = get_object_or_404(Stream, id=stream_id, class_group__school=school)

        # Create assignment if it doesn't already exist
        assignment, created = TeacherSubjectAssignment.objects.get_or_create(
            school=school,
            class_obj=class_obj,
            stream=stream,
            subject=subject,
            teacher=teacher,
        )

        messages.success(request, "Subject assigned to teacher successfully.")

    return redirect("manage_teachers")   
 
