from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.db import transaction

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from .models import School, DirectorOfStudies, Dormitory, Term, Class, Subject, GradingPolicy, StudentMark, ClassSubject
from django.db import IntegrityError
from students.models import Student
from schools.models import School, Dormitory, DirectorOfStudies, Term
from schools.models import Class, Teacher, Subject, TeacherSubject
User = get_user_model()
def superuser_required(view_func):
    return user_passes_test(lambda u: u.is_superuser)(view_func)
@login_required
@login_required
def superuser_dashboard(request):

    # ALL SCHOOLS
    schools = School.objects.all().order_by("-id")

    # COUNTS
    active_schools = School.objects.filter(is_active=True).count()

    # SAFE DEFAULTS
    pending_vouchers = 0
    vouchers = []
    queries = []

    # IF MODELS EXIST ENABLE THEM
    try:
        from .models import VoucherRequest

        vouchers = VoucherRequest.objects.filter(
            status="pending"
        ).order_by("-id")

        pending_vouchers = vouchers.count()

    except:
        pass

    try:
        from .models import DOSQuery

        queries = DOSQuery.objects.all().order_by("-id")

    except:
        pass

    context = {
        "schools": schools,
        "active_schools": active_schools,
        "pending_vouchers": pending_vouchers,
        "vouchers": vouchers,
        "queries": queries,
    }

    return render(
        request,
        "dashboards/superuser.html",
        context
    )
def landing_page(request):
    return render(request, "dashboards/landing.html")
@login_required
def dos_dashboard(request):
    school = request.user.school

    context = {
        "school": school,
        "classes": Class.objects.filter(school=school),
        "students": Student.objects.filter(school=school),
        "dorms": Dormitory.objects.filter(school=school),
    }

    return render(request, "dashboards/dos.html", context)

@login_required
def principal_dashboard(request):
    school = request.user.school

    return render(request, "dashboards/principal.html", {
        "school": school,
        "student_count": Student.objects.filter(school=school).count(),
        "teacher_count": 0,
        "dorm_count": Dormitory.objects.filter(school=school).count(),
    })

@login_required
def manage_classes(request):
    school = request.user.school

    classes = Class.objects.filter(school=school)

    return render(request, "dos/classes.html", {
        "classes": classes
    })
    
    
@login_required

def add_class(request):
    
    if request.method == "POST":

        try:

            name = request.POST.get("name")
            level = request.POST.get("level")

            Class.objects.create(
                school=request.user.school,
                name=name,
                level=level
            )

            messages.success(
                request,
                "Class created successfully."
            )

        except Exception as e:

            messages.error(
                request,
                f"System Error: {str(e)}"
            )

    return redirect("dos_dashboard")
def edit_class(request, class_id):
    school = request.user.school

    school_class = get_object_or_404(
        Class,
        id=class_id,
        school=school
    )

    if request.method == "POST":
        school_class.name = request.POST.get("name")
        school_class.code = request.POST.get("code")
        school_class.save()

        messages.success(request, "Class updated successfully.")
        return redirect("manage_classes")

    return render(request, "dos/edit_class.html", {
        "school_class": school_class
    })
@login_required
def delete_class(request, class_id):
    school = request.user.school

    school_class = get_object_or_404(
        Class,
        id=class_id,
        school=school
    )

    school_class.delete()

    messages.success(request, "Class deleted successfully.")
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

        # AUTO EMAIL (FIXED YOUR ERROR)
        email = f"{admission_number}@school.local"

        user = User.objects.create_user(
            username=admission_number,
            email=email,
            password="student123"
        )

        Student.objects.create(
            user=user,
            school=school,
            name=name,
            admission_number=admission_number,
            gender=gender,
            current_class=school_class
        )

        messages.success(request, "Student added successfully.")

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

    return render(request, "dos/print_class_list.html", {
        "school_class": school_class,
        "students": students
    })
    
@login_required
def download_class_list_pdf(request, class_id):
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

    # This is a placeholder function. The actual implementation would generate a PDF using ReportLab or similar library.
    return HttpResponse("PDF download will be implemented here.")
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

        user = User.objects.create_user(
            username=username,
            email=email,
            password="password123",
            role=role,
            school=school
        )

        messages.success(request, f"{role.replace('_', ' ').title()} account created successfully.")

    return redirect("dos_dashboard")

def manage_staff(request):
    school = request.user.school

    staff = User.objects.filter(school=school).exclude(is_superuser=True)

    return render(request, "dos/staff.html", {
        "staff": staff
    })
    
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from users.models import CustomUser
from .models import School, DirectorOfStudies


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
    
def deactivate_school(request, school_id):
    school = get_object_or_404(School, id=school_id)
    school.is_active = False
    school.save()
    messages.success(request, "School deactivated successfully.")
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import School

from django import forms
from .models import School

class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = "__all__"
        
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import School

@login_required
def add_school(request):

    if request.method == "POST":

        name = request.POST.get("name")
        address = request.POST.get("address")
        phone = request.POST.get("phone")
        email = request.POST.get("email")

        principal_name = request.POST.get("principal_name")
        principal_contact = request.POST.get("principal_contact")

        subscription_balance = request.POST.get(
            "subscription_balance"
        ) or 0

        logo = request.FILES.get("logo")

        School.objects.create(
            name=name,
            address=address,
            phone=phone,
            email=email,
            principal_name=principal_name,
            principal_contact=principal_contact,
            subscription_balance=subscription_balance,
            logo=logo,
        )

        messages.success(
            request,
            "School added successfully."
        )

    return redirect("superuser_dashboard")      


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
    
def delete_school(request, school_id):
    school = get_object_or_404(School, id=school_id)
    school.delete()
    messages.success(request, "School deleted successfully.")
    return redirect("manage_schools")
    
def manage_terms(request):
    school = request.user.school

    terms = Term.objects.filter(school=school)

    return render(request, "dos/terms.html", {
        "terms": terms
    })  
def reply_query(request, query_id):
    # This is a placeholder function. The actual implementation would depend on how queries are structured in your models.
    messages.info(request, "Replying to queries is not implemented yet.")
    return redirect("dos_dashboard")
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
def manage_exams(request):
    school = request.user.school

    # This is a placeholder function. The actual implementation would depend on how you manage exams in your models.
    return render(request, "dos/manage_grading.html", {
        "exams": []
    })
def enter_marks(request):
    school = request.user.school

    classes = ClassSubject.objects.filter(school=school).select_related("class_name", "subject")
    terms = Term.objects.filter(school=school)

    context = {
        "classes": classes,
        "terms": terms,
    }
    return render(request, "exams/enter_marks.html", context)

def load_students_for_marks(request):
    class_subject_id = request.GET.get("class_subject")
    term_id = request.GET.get("term")

    class_subject = get_object_or_404(ClassSubject, id=class_subject_id)
    term = get_object_or_404(Term, id=term_id)

    students = Student.objects.filter(current_class=class_subject.class_name)

    return render(request, "exams/partials/marks_table.html", {
        "students": students,
        "class_subject": class_subject,
        "term": term
    })
    
@transaction.atomic
def save_marks(request):
    if request.method == "POST":

        class_subject_id = request.POST.get("class_subject")
        term_id = request.POST.get("term")

        class_subject = get_object_or_404(ClassSubject, id=class_subject_id)
        term = get_object_or_404(Term, id=term_id)

        grading = GradingPolicy.objects.filter(
            school=class_subject.school
        )

        for key, value in request.POST.items():
            if key.startswith("student_"):
                student_id = key.split("_")[1]
                marks = float(value)

                student = Student.objects.get(id=student_id)

                # -------------------------
                # GET GRADE
                # -------------------------
                grade_obj = grading.filter(
                    min_score__lte=marks,
                    max_score__gte=marks
                ).first()

                grade = grade_obj.grade_letter if grade_obj else ""
                points = grade_obj.points if grade_obj else 0

                # -------------------------
                # SAVE OR UPDATE
                # -------------------------
                StudentMark.objects.update_or_create(
                    student=student,
                    class_subject=class_subject,
                    term=term,
                    defaults={
                        "marks": marks,
                        "grade": grade,
                        "points": points
                    }
                )

        messages.success(request, "Marks saved successfully")
        return redirect("enter_marks")    

def view_reports(request):
    school = request.user.school

    # This is a placeholder function. The actual implementation would depend on how you generate reports in your models.
    return render(request, "exams/report_center.html", {
        "reports": []
    })              
from students.models import Student
from exams.models import Exam
from .models import Class


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

    
def generate_marksheets(request):
    school = request.user.school

    # This is a placeholder function. The actual implementation would depend on how you generate marksheets in your models.
    return render(request, "exams/marksheets.html", {
        "students": Student.objects.filter(school=school),
        "classes": Class.objects.filter(school=school)
    })
    
def generate_merit_list(request):
    school = request.user.school

    # This is a placeholder function. The actual implementation would depend on how you generate merit lists in your models.
    return render(request, "dos/merit_list.html", {
        "students": Student.objects.filter(school=school).order_by("-current_class__name", "name")
    })  
from .models import (
    GradingPolicy,
    StudentMark,
    Subject,
    ClassSubject,
    Stream
)

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
    
@login_required
def add_subject(request):       
    school = request.user.school

    if request.method == "POST":
        name = request.POST.get("name")
        code = request.POST.get("code")

        Subject.objects.create(
            name=name,
            code=code,
            school=school
        )

        messages.success(request, "Subject added successfully.")

    return redirect("manage_subjects")

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
                            
def assign_teacher_subject(request):
    school = request.user.school

    teachers = Teacher.objects.filter(school=school)
    subjects = Subject.objects.filter(school=school)

    if request.method == "POST":
        teacher_id = request.POST.get("teacher")
        subject_id = request.POST.get("subject")

        teacher = get_object_or_404(Teacher, id=teacher_id)
        subject = get_object_or_404(Subject, id=subject_id)

        TeacherSubject.objects.update_or_create(
            teacher=teacher,
            subject=subject
        )

        messages.success(request, "Teacher assigned to subject successfully")
        return redirect("assign_teacher_subject")

    return render(request, "schools/assign_teacher_subject.html", {
        "teachers": teachers,
        "subjects": subjects
    })
    
def assign_teacher_subject(request):
    school = request.user.school

    teachers = Teacher.objects.filter(school=school)
    subjects = Subject.objects.filter(school=school)

    if request.method == "POST":
        teacher_id = request.POST.get("teacher")
        subject_id = request.POST.get("subject")

        teacher = get_object_or_404(Teacher, id=teacher_id)
        subject = get_object_or_404(Subject, id=subject_id)

        TeacherSubject.objects.update_or_create(
            teacher=teacher,
            subject=subject
        )

        messages.success(request, "Teacher assigned to subject successfully")
        return redirect("assign_teacher_subject")

    return render(request, "schools/assign_teacher_subject.html", {
        "teachers": teachers,
        "subjects": subjects
    })
        
                                 