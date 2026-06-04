import csv
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect

from assignments.models import Assignment, Submission
from assignments.models import Submission
from schools.models import Notification, Principal, Subject
from students.models import Student
from users.models import CustomUser
from .models import Teacher, ClassTeacherAssignment, TeacherSubjectAssignment
from classes.models import Stream
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from .models import Teacher
from classes.models import Class
from django.contrib.auth.decorators import login_required
from users.models import CustomUser
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from .models import Teacher
from django.shortcuts import render, redirect
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from classes.models import Class
from .models import Teacher

def assign_teacher_class(request):
    school = request.user.school

    if request.method == "POST":

        teacher_id = request.POST.get("teacher")
        class_id = request.POST.get("class")
        stream_id = request.POST.get("stream")

        teacher = get_object_or_404(Teacher, id=teacher_id, school=school)
        class_obj = get_object_or_404(Class, id=class_id, school=school)

        stream = None
        if stream_id:
            stream = get_object_or_404(Stream, id=stream_id, class_group__school=school)

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
                role="teacher"
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
                        stream=None,
                        teacher=teacher
                    )
                except Exception:
                    pass

            messages.success(
                request,
                "Teacher added successfully."
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

    subjects = []
    seen = set()
    for sa in subject_assignments:
        if sa.subject_id not in seen:
            seen.add(sa.subject_id)
            subjects.append(sa.subject)

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
    # CONTEXT
    # =========================
    return render(request, "teachers/dashboard.html", {
        "teacher": teacher,
        "assigned_classes": assigned_classes,
        "subjects": subjects,
        "students": students,
        "assignments": assignments,
        "submissions": submissions,
        "notifications": notifications,
        "unread_notifications": unread_notifications,
    })    


@login_required
def edit_teacher(request, teacher_id):
    teacher = get_object_or_404(Teacher, id=teacher_id, school=request.user.school)
    subjects = Subject.objects.filter(school=request.user.school)
    classes = Class.objects.filter(school=request.user.school)
    if request.method == "POST":
        teacher.name = request.POST["name"]
        teacher.phone = request.POST["phone"]
        teacher.role = request.POST["role"]

        class_id = request.POST.get("assigned_class")
        if class_id:
            class_obj = get_object_or_404(Class, id=class_id, school=request.user.school)
            # Remove any previous class assignments for this teacher and set the new one
            ClassTeacherAssignment.objects.filter(teacher=teacher).delete()
            ClassTeacherAssignment.objects.create(
                school=request.user.school,
                class_obj=class_obj,
                stream=None,
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
 
