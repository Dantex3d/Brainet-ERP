# teachers/admin.py
from django.contrib import admin
from .models import Teacher

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('name', 'school', 'role', 'subject', 'assigned_class', 'is_active')
    list_filter = ('school', 'role', 'is_active')
    search_fields = ('name', 'email', 'phone')
