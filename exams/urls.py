from django.urls import path
from . import views

urlpatterns = [
    path("class-report/", views.exams_class_report, name="exams_class_report"),
]
