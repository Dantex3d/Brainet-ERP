from django.contrib import admin
from .models import Exam, Mark


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('name', 'school', 'term', 'start_date', 'end_date', 'is_open')
    list_filter = ('school', 'term', 'is_open')
    search_fields = ('name',)


@admin.register(Mark)
class MarkAdmin(admin.ModelAdmin):
    list_display = ('exam', 'student', 'subject', 'teacher', 'score')
    list_filter = ('exam', 'teacher')
    search_fields = ('student__name', 'subject')