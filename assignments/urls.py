from django.urls import path
from . import views

urlpatterns = [
    path("create/", views.create_assignment, name="create_assignment"),
    path("teacher/", views.teacher_assignments, name="teacher_assignments"),
    path("student/", views.student_assignments, name="student_assignments"),
    path("submit/<int:assignment_id>/", views.submit_assignment, name="submit_assignment"),
    path("submissions/<int:assignment_id>/", views.assignment_submissions, name="assignment_submissions"),
    path("submission/<int:submission_id>/mark/",views.mark_submission,name="mark_submission"),
    path("api/class-streams/", views.get_class_streams, name="get_class_streams"),
    path("api/class-subjects/", views.get_class_subjects, name="get_class_subjects"),
]