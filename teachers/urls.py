from django.urls import path
from . import views

urlpatterns = [
    path("manage/", views.manage_teachers, name="manage_teachers"),
    path("export/csv/", views.export_teachers, name="export_teachers"),
    path("export/pdf/", views.export_teachers_pdf, name="export_teachers_pdf"),
    path("add/", views.add_teacher, name="add_teacher"),
    path("<int:teacher_id>/edit/", views.edit_teacher, name="edit_teacher"),
    path("<int:teacher_id>/delete/", views.delete_teacher, name="delete_teacher"),
    path("dashboard/", views.teacher_dashboard, name="teacher_dashboard"),
    path("subject-teacher/dashboard/", views.teacher_dashboard, name="subject_teacher_dashboard"),
    path("online-classes/", views.teacher_online_classes, name="teacher_online_classes"),
    path("online-classes/<int:online_class_id>/", views.teacher_online_class_detail, name="teacher_online_class_detail"),
    path("assign-teacher-subject/", views.assign_teacher_subject, name="assign_teacher_subject"),
    path("assign-class/", views.assign_teacher_class, name="assign_teacher_class"),
]
