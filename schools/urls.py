from django.urls import path
from . import views


urlpatterns = [

    # =====================================================
    # LANDING
    # =====================================================

    path("", views.landing_page, name="landing_page"),


    # =====================================================
    # SUPERUSER
    # =====================================================

    path(
        "superuser/",
        views.superuser_dashboard,
        name="superuser_dashboard"
    ),

    path(
        "superuser/create-staff/",
        views.create_staff,
        name="create_staff"
    ),

    path(
        "superuser/register-dos/",
        views.register_dos_by_superuser,
        name="register_dos_by_superuser"
    ),


    # =====================================================
    # SCHOOL MANAGEMENT
    # =====================================================

    path(
        "schools/add/",
        views.add_school,
        name="add_school"
    ),

    path(
        "schools/<int:school_id>/view/",
        views.view_school,
        name="view_school"
    ),

    path(
        "schools/<int:school_id>/edit/",
        views.edit_school,
        name="edit_school"
    ),

    path(
        "schools/<int:school_id>/activate/",
        views.activate_school,
        name="activate_school"
    ),

    path(
        "schools/<int:school_id>/deactivate/",
        views.deactivate_school,
        name="deactivate_school"
    ),

    path(
        "schools/<int:school_id>/delete/",
        views.delete_school,
        name="delete_school"
    ),
    path(
        "queries/<int:query_id>/reply/",
        views.reply_query,
        name="reply_query"
    ),


    # =====================================================
    # DOS DASHBOARD
    # =====================================================

    path(
        "dos/",
        views.dos_dashboard,
        name="dos_dashboard"
    ),

    path(
        "dos/open-exams/",
        views.open_exam_window,
        name="open_exam_window"
    ),

    path(
        "dos/close-exams/",
        views.close_exam_window,
        name="close_exam_window"
    ),


    # =====================================================
    # STUDENTS
    # =====================================================

    path(
        "students/",
        views.manage_students,
        name="manage_students"
    ),

    path(
        "students/add/",
        views.add_student,
        name="add_student"
    ),

    path(
        "students/<int:student_id>/edit/",
        views.edit_student,
        name="edit_student"
    ),

    path(
        "students/download/",
        views.download_student_list,
        name="download_student_list"
    ),


    # =====================================================
    # CLASSES
    # =====================================================

    path(
        "classes/",
        views.manage_classes,
        name="manage_classes"
    ),

    path(
        "classes/add/",
        views.add_class,
        name="add_class"
    ),

    path(
        "classes/<int:class_id>/edit/",
        views.edit_class,
        name="edit_class"
    ),

    path(
        "classes/<int:class_id>/delete/",
        views.delete_class,
        name="delete_class"
    ),

    path(
        "classes/<int:class_id>/students/",
        views.view_class_students,
        name="view_class_students"
    ),
    
    path(
        "classes/<int:class_id>/students/",
        views.class_lists,
        name="class_lists"
    ),
path(
    'classes/',
    views.class_lists,
    name='class_lists'
),

    path(
        "classes/<int:class_id>/pdf/",
        views.download_class_list_pdf,
        name="download_class_list_pdf"
    ),


    # =====================================================
    # SUBJECTS
    # =====================================================

    path(
        "subjects/",
        views.manage_subjects,
        name="manage_subjects"
    ),

    path(
        "subjects/add/",
        views.add_subject,
        name="add_subject"
    ),

    path(
        "subjects/<int:subject_id>/edit/",
        views.edit_subject,
        name="edit_subject"
    ),

    path(
        "subjects/<int:subject_id>/delete/",
        views.delete_subject,
        name="delete_subject"
    ),


    # =====================================================
    # CLASS SUBJECT ASSIGNMENT
    # =====================================================

    path(
        "classes/<int:class_id>/assign-subjects/",
        views.assign_subjects_to_class,
        name="assign_subjects_to_class"
    ),


    # =====================================================
    # TEACHER SUBJECT ASSIGNMENT
    # =====================================================

    path(
        "teachers/assign-subjects/",
        views.assign_teacher_subject,
        name="assign_teacher_subject"
    ),


    # =====================================================
    # DORMITORIES
    # =====================================================

    path(
        "dormitories/",
        views.manage_dorms,
        name="manage_dorms"
    ),

    path(
        "dormitories/add/",
        views.add_dorm,
        name="add_dorm"
    ),

    path(
        "dormitories/<int:dorm_id>/edit/",
        views.edit_dorm,
        name="edit_dorm"
    ),

    path(
        "dormitories/<int:dorm_id>/delete/",
        views.delete_dorm,
        name="delete_dorm"
    ),

    path(
        "dormitories/<int:dorm_id>/students/",
        views.view_dorm_students,
        name="view_dorm_students"
    ),
    path(
    'dorms/',
    views.dormitory_lists,
    name='dormitory_lists'
),

    # =====================================================
    # EXAMS
    # =====================================================

    path(
        "exams/",
        views.manage_exams,
        name="manage_exams"
    ),

    path(
        "exams/enter-marks/",
        views.enter_marks,
        name="enter_marks"
    ),

    path(
        "exams/marksheets/",
        views.generate_marksheets,
        name="generate_marksheets"
    ),

    path(
        "exams/merit-list/",
        views.generate_merit_list,
        name="generate_merit_list"
    ),


    # =====================================================
    # REPORT FORMS
    # =====================================================

path(
    'reports/',
    views.report_center,
    name='report_center'
),

    
    # SUBJECTS
path(
    "dos/manage-subjects/",
    views.manage_subjects,
    name="manage_subjects"
),

path(
    "dos/add-subject/",
    views.add_subject,
    name="add_subject"
),

path(
    "dos/edit-subject/<int:subject_id>/",
    views.edit_subject,
    name="edit_subject"
),

path(
    "dos/delete-subject/<int:subject_id>/",
    views.delete_subject,
    name="delete_subject"
),

# CLASS SUBJECT ASSIGNMENT
path(
    "dos/class/<int:class_id>/assign-subjects/",
    views.assign_subjects_to_class,
    name="assign_subjects_to_class"
),

path(
    "dos/delete-class-subject/<int:assignment_id>/",
    views.delete_class_subject,
    name="delete_class_subject"
),
# =====================================================
# GRADING SYSTEM
# =====================================================

path(
    "dos/manage-grading/",
    views.manage_grading,
    name="manage_grading"
),

path(
    "dos/add-grading/",
    views.add_grading_policy,
    name="add_grading_policy"
),

path(
    "dos/edit-grading/<int:grading_id>/",
    views.edit_grading_policy,
    name="edit_grading_policy"
),

path(
    "dos/delete-grading/<int:grading_id>/",
    views.delete_grading_policy,
    name="delete_grading_policy"
),
path("principal/enter-marks/", views.enter_marks, name="enter_marks"),
path("principal/load-students/", views.load_students_for_marks, name="load_students_for_marks"),
path("principal/save-marks/", views.save_marks, name="save_marks"),
]

