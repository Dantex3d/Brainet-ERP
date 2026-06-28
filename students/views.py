from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse

from exams.models import Exam, Mark
from .models import Student
from schools.models import Class, Dormitory, Term

from subjects.models import ClassSubject
from schools.views import get_grade_and_points


User = get_user_model()


@login_required
def register_student(request):

    if request.user.role != 'dos':
        return redirect('dashboard')

    school = request.user.school

    if request.method == 'POST':

        name = request.POST['name']
        gender = request.POST['gender']
        class_id = request.POST['class_id']
        stream_id = request.POST.get('stream_id')
        dormitory_id = request.POST.get('dormitory_id')
        parent_phone = request.POST.get('parent_phone')

        total_students = Student.objects.filter(school=school).count() + 1
        admission_number = f"{school.id}STD{total_students:04d}"

        password = "123456"

        user = User.objects.create_user(
            username=admission_number,
            password=password,
            role='student',
            school=school
        )

        student = Student.objects.create(
            user=user,
            school=school,
            admission_number=admission_number,
            name=name,
            gender=gender,
            current_class_id=class_id,
            stream_id=stream_id if stream_id else None,
            dormitory_id=dormitory_id,
            parent_phone=parent_phone
        )
        
        # Auto-enroll student in class subjects
        from subjects.models import ClassSubject, StudentSubject
        class_subjects = ClassSubject.objects.filter(
            school=school,
            class_name_id=class_id
        )
        for cs in class_subjects:
            StudentSubject.objects.get_or_create(
                student=student,
                subject=cs.subject,
                defaults={'class_subject': cs}
            )

        return redirect('dashboard')

    from classes.models import Stream
    return render(request, 'students/register_student.html', {
        'classes': Class.objects.filter(school=school),
        'streams': Stream.objects.filter(class_group__school=school),
        'dormitories': Dormitory.objects.filter(school=school)
    })
    
    
def students_by_subject(request, subject_id):
    
    cs = get_object_or_404(ClassSubject, id=subject_id)

    students = Student.objects.filter(
        school=cs.school,
        current_class=cs.class_name
    )

    data = [
        {"id": s.id, "name": s.name}
        for s in students
    ]

    return JsonResponse({"students": data})  

from django.contrib.auth import authenticate
from .models import Student, StudentLoginLog


def student_login(request):

    error = None

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        ip = request.META.get("REMOTE_ADDR")
        browser = request.META.get("HTTP_USER_AGENT")

        if user and user.role == "student":

            student = Student.objects.get(user=user)

            request.session["student_id"] = student.id

            # SUCCESS LOG
            StudentLoginLog.objects.create(
                student=student,
                username=username,
                status="success",
                ip_address=ip,
                user_agent=browser
            )

            return redirect("student_dashboard")

        else:

            # FAILED LOG
            StudentLoginLog.objects.create(
                username=username,
                status="failed",
                ip_address=ip,
                user_agent=browser
            )

            error = "Invalid username or password"

    return render(request, "students/login.html", {
        "error": error
    })  
    
from .models import StudentLoginLog


@login_required
def student_login_logs(request):

    school = request.user.school

    logs = StudentLoginLog.objects.filter(
        student__school=school
    ).select_related(
        "student"
    ).order_by("-created_at")[:300]

    return render(
        request,
        "students/login_logs.html",
        {
            "logs": logs
        }
    )