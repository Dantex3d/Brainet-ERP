from pyexpat.errors import messages

from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required

from subjects.models import Subject, ClassSubject
from classes.models import Class


@login_required
def manage_subjects(request):

    school = request.user.school

    subjects = Subject.objects.filter(
        school=school
    ).order_by("name")

    return render(
        request,
        "dos/manage_subjects.html",
        {
            "subjects": subjects
        }
    )
    
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Subject

def add_subject(request):       
    school = request.user.school  # assumes User has a school FK

    if request.method == "POST":
        name = request.POST.get("name")
        short_name = request.POST.get("short_name") 
        code = request.POST.get("code")

        Subject.objects.create(
            name=name,
            short_name=short_name,
            code=code,
            school=school
        )

        messages.success(request, "Subject added successfully ✅")
        return redirect("manage_subjects")  # redirect after POST

    # For GET requests, show the manage subjects page
    subjects = Subject.objects.filter(school=school)
    return render(request, "subjects/manage_subjects.html", {"subjects": subjects})


@login_required
def edit_subject(request, subject_id):  
    school = request.user.school

    subject = get_object_or_404(
        Subject,
        id=subject_id,
        school=school
    )

    if request.method == "POST":
        subject.name = request.POST.get("name")
        subject.code = request.POST.get("code")
        subject.save()

        messages.success(request, "Subject updated successfully.")
        return redirect("manage_subjects")

    return render(request, "dos/edit_subject.html", {
        "subject": subject
    })
    
@login_required
def delete_subject(request, subject_id):    
    school = request.user.school

    subject = get_object_or_404(
        Subject,
        id=subject_id,
        school=school
    )

    subject.delete()

    messages.success(request, "Subject deleted successfully.")
    return redirect("manage_subjects")   

@login_required
def assign_subjects_to_class(request, class_id):

    school = request.user.school

    school_class = get_object_or_404(
        Class,
        id=class_id,
        school=school
    )

    subjects = Subject.objects.filter(
        school=school
    )

    assigned_subjects = ClassSubject.objects.filter(
        school_class=school_class
    )

    if request.method == "POST":

        subject_id = request.POST.get("subject")
        teacher_id = request.POST.get("teacher")

        subject = get_object_or_404(
            Subject,
            id=subject_id
        )

        from teachers.models import Teacher

        teacher = get_object_or_404(
            Teacher,
            id=teacher_id
        )

        ClassSubject.objects.create(
            school=school,
            school_class=school_class,
            subject=subject,
            teacher=teacher
        )

        messages.success(
            request,
            "Subject assigned successfully."
        )

        return redirect(
            "assign_subjects_to_class",
            class_id=school_class.id
        )

    from teachers.models import Teacher

    teachers = Teacher.objects.filter(
        school=school
    )

    return render(
        request,
        "dos/assign_subjects.html",
        {
            "school_class": school_class,
            "subjects": subjects,
            "teachers": teachers,
            "assigned_subjects": assigned_subjects
        }
    ) 
    
@login_required
def delete_class_subject(request, assignment_id):

    school = request.user.school

    assignment = get_object_or_404(
        ClassSubject,
        id=assignment_id,
        school=school
    )

    class_id = assignment.school_class.id

    assignment.delete()

    messages.success(
        request,
        "Subject assignment deleted."
    )

    return redirect(
        "assign_subjects_to_class",
        class_id=class_id
    ) 

   