from django.contrib import admin

from classes.models import Stream
from .models import Dormitory, School, DirectorOfStudies,Term, Class
from .views import edit_school, view_school
@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'phone', 'email', 'is_active')
    search_fields = ('name', 'phone', 'email')
    list_filter = ('is_active',)

@admin.register(DirectorOfStudies)
class DOSAdmin(admin.ModelAdmin):
    list_display = ('name', 'school', 'email', 'phone', 'email_verified', 'phone_verified')
    search_fields = ('name', 'email', 'phone')
    list_filter = ('email_verified', 'phone_verified')
@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ('school', 'name', 'opening_date', 'closing_date', 'status')
    list_filter = ('status', 'school')
    search_fields = ('name',)

@admin.register(Dormitory)
class DormitoryAdmin(admin.ModelAdmin):
    list_display = ('name','school','capacity','supervisor')
    search_fields = ('name','supervisor')
    list_filter = ('school',)

@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'school')
    list_filter = ('school', 'level')
    search_fields = ('name', 'school__name')
