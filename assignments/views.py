from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count

from .models import Assignment, Submission
from schools.models import Notification
from classes.models import Class
from subjects.models import Subject
from students.models import Student


# ==========================================
# VIEW ASSIGNMENT SUBMISSIONS (TEACHER)
# ==========================================
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

    classes = (
        Class.objects
        .filter(school=school)
        .order_by("name")
    )

    # limit subjects to those the teacher is assigned to
    from teachers.models import TeacherSubjectAssignment
    assigned_subject_ids = TeacherSubjectAssignment.objects.filter(
        teacher=teacher,
        school=school
    ).values_list("subject_id", flat=True).distinct()

    subjects = (
        Subject.objects
        .filter(id__in=assigned_subject_ids, school=school)
        .order_by("name")
    )

    if request.method == "POST":

        try:

            title = request.POST.get("title")
            instructions = request.POST.get("instructions")
            class_id = request.POST.get("class_id")
            subject_id = request.POST.get("subject_id")
            due_date = request.POST.get("due_date")
            total_marks = request.POST.get("total_marks") or 100

            # uploaded assignment file
            attachment = request.FILES.get("attachment")

            if not title:
                messages.error(request, "Assignment title required")
                return redirect("create_assignment")

            # validate that the teacher is assigned to this subject for the chosen class
            if subject_id and class_id:
                allowed = TeacherSubjectAssignment.objects.filter(
                    teacher=teacher,
                    school=school,
                    subject_id=subject_id,
                    class_obj_id=class_id
                ).exists()
                if not allowed:
                    messages.error(request, "You are not assigned to that subject for the selected class.")
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

