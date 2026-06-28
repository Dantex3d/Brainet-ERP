from django.urls import path
from . import views

urlpatterns = [

    path("manage/", views.manage_subjects, name="manage_subjects"),

    path("add/", views.add_subject, name="add_subject"),

    path("edit/<int:id>/", views.edit_subject, name="edit_subject"),

    path("delete/<int:id>/", views.delete_subject, name="delete_subject"),
    path("remove-class-subject/<int:assignment_id>/", views.delete_class_subject, name="delete_class_subject"),
   
    path("assign-subjects-to-class/<int:class_id>/", views.assign_subjects_to_class, name="assign_subjects_to_class"),
    path("dos/manage-subjects/", views.manage_subjects, name="manage_subjects"),
    path("dos/add-subject/", views.add_subject, name="add_subject"),
    path("dos/edit-subject/<int:subject_id>/", views.edit_subject, name="edit_subject"),
    path("dos/delete-subject/<int:subject_id>/", views.delete_subject, name="delete_subject"),
    

]