from django.contrib import admin
from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'admission_number',
        'gender',
        'current_class',
        'school',
        'status',
    )

    list_filter = (
        'school',
        'current_class',
        'gender',
        'status',
    )

    search_fields = (
        'name',
        'admission_number',
    )

    ordering = (
        'name',
    )