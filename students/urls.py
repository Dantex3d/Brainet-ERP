from django.urls import path
from . import views

urlpatterns = [

    path(
        'register/',
        views.register_student,
        name='register_student'
    ),
# students/urls.py
path("by-class-subject/<int:class_subject_id>/", views.students_by_class_subject),
]