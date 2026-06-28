from django.contrib import admin

from .models import Exam


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "name",
        "school",
        "exam_type",
        "term",
        "is_active",
        "created_at",
    )

    list_filter = (
        "exam_type",
        "term",
        "is_active",
    )

    search_fields = (
        "name",
        "school__name",
    )

    ordering = (
        "-created_at",
    )