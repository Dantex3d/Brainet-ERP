# reports/admin.py
from django.contrib import admin
from .models import Report

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('student','exam','term','generated_at')
    search_fields = ('student__full_name','exam__name')
    list_filter = ('term','exam')
