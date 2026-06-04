from django.urls import path
from . import views

urlpatterns = [

    path(
        'register/',
        views.register_student,
        name='register_student'
    ),
# students/urls.py
path("by-subject/<int:subject_id>/", views.students_by_subject),
 path("student/login/", views.student_login, name="student_login"),
 path("student-login-logs/",views.student_login_logs,name="student_login_logs"),
]