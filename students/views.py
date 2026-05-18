from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model

from .models import Student
from schools.models import Class, Dormitory

User = get_user_model()


@login_required
def register_student(request):

    if request.user.role != 'dos':
        return redirect('dashboard')

    if request.method == 'POST':

        name = request.POST['name']
        gender = request.POST['gender']
        class_id = request.POST['class_id']
        dormitory_id = request.POST['dormitory_id']
        parent_phone = request.POST['parent_phone']

        school = request.user.school

        # auto admission number
        total_students = Student.objects.filter(
            school=school
        ).count() + 1

        admission_number = f"{school.id}STD{total_students:04d}"

        # default password
        password = "123456"

        # create user account
        user = User.objects.create_user(
            username=admission_number,
            password=password,
            role='student',
            school=school
        )

        # create student profile
        Student.objects.create(
            user=user,
            school=school,
            admission_number=admission_number,
            name=name,
            gender=gender,
            current_class_id=class_id,
            dormitory_id=dormitory_id,
            parent_phone=parent_phone
        )

        return redirect('dashboard')

    classes = Class.objects.filter(
        school=request.user.school
    )

    dormitories = Dormitory.objects.filter(
        school=request.user.school
    )

    return render(request, 'students/register_student.html', {
        'classes': classes,
        'dormitories': dormitories
    })
    
# students/views.py

from django.http import JsonResponse
from schools.models import ClassSubject
from .models import Student


def students_by_class_subject(request, class_subject_id):
    cs = ClassSubject.objects.get(id=class_subject_id)

    students = Student.objects.filter(current_class=cs.class_name)

    data = [
        {"id": s.id, "name": s.name}
        for s in students
    ]

    return JsonResponse({"students": data})    