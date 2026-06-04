from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
import json

from .models import Assignment, Submission
from schools.models import Notification
from classes.models import Class, Stream
from subjects.models import Subject
from students.models import Student
from teachers.models import TeacherSubjectAssignment


# ==========================================
# API: GET STREAMS FOR CLASS
# ==========================================
@login_required
def get_class_streams(request):
    """Fetch streams the teacher is assigned to in a class"""
    class_id = request.GET.get("class_id")
    
    if not class_id:
        return JsonResponse({"error": "class_id required"}, status=400)
    
    teacher = request.user.teacher
    school = request.user.school
    
    # Get streams the teacher is assigned to in this class
    stream_ids = TeacherSubjectAssignment.objects.filter(
        teacher=teacher,
        school=school,
        class_obj_id=class_id,
        stream__isnull=False
    ).values_list("stream_id", flat=True).distinct()
    
    # Fetch the actual stream objects
    streams = Stream.objects.filter(
        id__in=stream_ids
    ).order_by("name").values("id", "name")
    
    return JsonResponse(list(streams), safe=False)


# ==========================================
# API: GET SUBJECTS FOR CLASS+STREAM
# ==========================================
@login_required
def get_class_subjects(request):
    """Fetch subjects the teacher teaches for a class+stream combination"""
    class_id = request.GET.get("class_id")
    stream_id = request.GET.get("stream_id")
    
    if not class_id:
        return JsonResponse({"error": "class_id required"}, status=400)
    
    teacher = request.user.teacher
    school = request.user.school
    
    # Build query for teacher's subject assignments
    query = TeacherSubjectAssignment.objects.filter(
        teacher=teacher,
        school=school,
        class_obj_id=class_id
    )
    
    # If stream is provided, filter by stream
    if stream_id:
        query = query.filter(stream_id=stream_id)
    
    # Get unique subjects
    subject_ids = query.values_list("subject_id", flat=True).distinct()
    subjects = Subject.objects.filter(
        id__in=subject_ids,
        school=school
    ).order_by("name").values("id", "name")
    
    return JsonResponse(list(subjects), safe=False)



@login_required
def assignment_submissions(request, assignment_id):
    teacher = request.user.teacher

    assignment = get_object_or_404(
        Assignment,
        id=assignment_id,
        teacher=teacher
    )

    submissions = (
        Submission.objects
        .filter(assignment=assignment)
        .select_related("student")
        .order_by("-submitted_at")
    )

    total_submissions = submissions.count()
    marked_submissions = submissions.filter(status="graded").count()   # 🔥 count graded
    pending_submissions = submissions.filter(status="submitted").count()  # 🔥 count submitted

    return render(
        request,
        "assignments/submissions.html",
        {
            "assignment": assignment,
            "submissions": submissions,
            "total_submissions": total_submissions,
            "marked_submissions": marked_submissions,
            "pending_submissions": pending_submissions,
        }
    )

# ==========================================
# CREATE ASSIGNMENT (TEACHER)
# ==========================================
@login_required
def create_assignment(request):

    teacher = request.user.teacher
    school = request.user.school

    # Get classes that the teacher is assigned to (has subject assignments in)
    assigned_class_ids = TeacherSubjectAssignment.objects.filter(
        teacher=teacher,
        school=school
    ).values_list("class_obj_id", flat=True).distinct()

    classes = (
        Class.objects
        .filter(school=school, id__in=assigned_class_ids)
        .order_by("name")
    )

    # Subjects will be loaded dynamically via AJAX based on class+stream selection
    # Initially empty (will be populated when user selects a class)
    subjects = Subject.objects.none()

    if request.method == "POST":

        try:

            title = request.POST.get("title")
            instructions = request.POST.get("instructions")
            class_id = request.POST.get("class_id")
            stream_id = request.POST.get("stream_id")
            subject_id = request.POST.get("subject_id")
            due_date = request.POST.get("due_date")
            total_marks = request.POST.get("total_marks") or 100

            # uploaded assignment file
            attachment = request.FILES.get("attachment")

            if not title:
                messages.error(request, "Assignment title required")
                return redirect("create_assignment")

            # Validate that the teacher is assigned to this subject for the chosen class+stream
            if subject_id and class_id:
                query = TeacherSubjectAssignment.objects.filter(
                    teacher=teacher,
                    school=school,
                    subject_id=subject_id,
                    class_obj_id=class_id
                )
                
                # If stream is selected, verify assignment includes that stream
                if stream_id:
                    query = query.filter(Q(stream_id=stream_id) | Q(stream__isnull=True))
                
                if not query.exists():
                    messages.error(request, "You are not assigned to that subject for the selected class/stream.")
                    return redirect("create_assignment")

            assignment = Assignment.objects.create(
                school=school,
                teacher=teacher,
                title=title,
                instructions=instructions,
                class_assigned_id=class_id,
                subject_id=subject_id,
                due_date=due_date,
                total_marks=total_marks,
                attachment=attachment
            )

            # ===================================
            # NOTIFY STUDENTS
            # ===================================
            students = Student.objects.filter(
                school=school,
                current_class_id=class_id
            )

            for student in students:

                Notification.objects.create(
                    school=school,
                    sender=request.user,
                    recipient=student.user,
                    title="New Assignment",
                    message=f"{title} has been posted."
                )

            messages.success(
                request,
                "Assignment created successfully"
            )

            return redirect("teacher_assignments")

        except Exception as e:

            messages.error(
                request,
                f"System Error: {str(e)}"
            )

            return redirect("create_assignment")

    return render(
        request,
        "assignments/create_assignment.html",
        {
            "classes": classes,
            "subjects": subjects,
        }
    )


# ==========================================
# TEACHER ASSIGNMENTS
# ==========================================
@login_required
def teacher_assignments(request):

    teacher = request.user.teacher

    assignments = (
        Assignment.objects
        .filter(teacher=teacher)
        .annotate(
            submission_count=Count("submissions")
        )
        .order_by("-created_at")
    )

    return render(
        request,
        "assignments/teacher_assignments.html",
        {
            "assignments": assignments
        }
    )


# ==========================================
# STUDENT ASSIGNMENTS
# ==========================================
@login_required
def student_assignments(request):

    student = request.user.student_profile

    assignments = (
        Assignment.objects
        .filter(
            class_assigned=student.current_class,
            is_active=True
        )
        .select_related(
            "subject",
            "teacher",
            "class_assigned"
        )
        .order_by("-created_at")
    )

    submitted_assignment_ids = Submission.objects.filter(
        student=student
    ).values_list(
        "assignment_id",
        flat=True
    )

    submissions = Submission.objects.filter(
        student=student
    ).select_related(
        "assignment"
    ).order_by("-submitted_at")

    return render(
        request,
        "assignments/student_assignments.html",
        {
            "student": student,
            "assignments": assignments,
            "submissions": submissions,
            "submitted_assignment_ids": submitted_assignment_ids,
        }
    )


# ==========================================
# SUBMIT ASSIGNMENT
# ==========================================
@login_required
def submit_assignment(request, assignment_id):

    student = request.user.student_profile

    assignment = get_object_or_404(
        Assignment,
        id=assignment_id,
        class_assigned=student.current_class
    )

    # prevent late unauthorized classes
    if assignment.class_assigned != student.current_class:

        messages.error(
            request,
            "Unauthorized assignment access"
        )

        return redirect("student_assignments")

    if request.method == "POST":

        try:

            uploaded_file = request.FILES.get("file")

            if not uploaded_file:

                messages.error(
                    request,
                    "Please select file"
                )

                return redirect("student_assignments")

            # ===================================
            # UPDATE OR CREATE SUBMISSION
            # ===================================
            submission, created = Submission.objects.update_or_create(

                assignment=assignment,
                student=student,

                defaults={
                    "school": student.school,
                    "file": uploaded_file,
                }
            )

            # ===================================
            # NOTIFY TEACHER
            # ===================================
            Notification.objects.create(
                school=assignment.school,
                sender=request.user,
                recipient=assignment.teacher.user,
                title="Assignment Submitted",
                message=f"{student.name} submitted {assignment.title}"
            )

            if created:

                messages.success(
                    request,
                    "Assignment submitted successfully"
                )

            else:

                messages.success(
                    request,
                    "Submission updated successfully"
                )

            return redirect("student_assignments")

        except Exception as e:

            messages.error(
                request,
                f"Submission Error: {str(e)}"
            )

            return redirect("student_assignments")

    return render(
        request,
        "assignments/submit_assignment.html",
        {
            "assignment": assignment
        }
    )
    
# ==========================================
# MARK SUBMISSION
# ==========================================
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from .models import Submission

@login_required
def mark_submission(request, submission_id):
    teacher = request.user.teacher

    submission = get_object_or_404(
        Submission.objects.select_related("assignment", "student"),
        id=submission_id,
        assignment__teacher=teacher
    )

    if request.method == "POST":
        try:
            score = request.POST.get("score")
            feedback = request.POST.get("feedback")

            # =========================
            # UPDATE SUBMISSION
            # =========================
            submission.score = score
            submission.feedback = feedback
            submission.status = "graded"   # 🔥 use status field instead of is_marked
            submission.save()

            # =========================
            # NOTIFY STUDENT
            # =========================
            Notification.objects.create(
                school=submission.student.school,
                sender=request.user,
                recipient=submission.student.user,
                title="Assignment Marked",
                message=(
                    f"Your assignment '{submission.assignment.title}' "
                    f"has been marked."
                )
            )

            messages.success(request, "Assignment marked successfully ✅")

        except Exception as e:
            messages.error(request, f"Marking Error: {str(e)}")

        return redirect("assignment_submissions", assignment_id=submission.assignment.id)

    return render(request, "assignments/mark_submission.html", {"submission": submission})

