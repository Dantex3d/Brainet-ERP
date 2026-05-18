# exams/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("enter-mark/", views.enter_mark),
    path("bulk-enter-marks/", views.bulk_enter_marks),
]