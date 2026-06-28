# classes/admin.py
from django.contrib import admin

class ClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'school')
    list_filter = ('school', 'level')
    search_fields = ('name', 'school__name')
class StreamAdmin(admin.ModelAdmin):
    list_display = ('name', 'class_group')
    list_filter = ('class_group__school',)
    search_fields = ('name', 'class_group__name')
