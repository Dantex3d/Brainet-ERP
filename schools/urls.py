from django.urls import path
from . import views

urlpatterns = [

    # =====================================================
    # LANDING
    # =====================================================
    path("", views.landing_page, name="landing_page"),
    path("mobile-app/", views.mobile_app, name="mobile_app"),
    path("features-demo/", views.features_demo, name="features_demo"),

    # =====================================================
    # SUPERUSER
    # =====================================================
    path("superuser/", views.superuser_dashboard, name="superuser_dashboard"),
    path("superuser/schools/", views.manage_schools, name="manage_schools"),
    path("superuser/principals/", views.manage_principals, name="manage_principals"),
    path("superuser/dos/", views.manage_dos, name="manage_dos"),
    path("superuser/create-staff/", views.create_staff, name="create_staff"),
    path("superuser/register-dos/", views.register_dos_by_superuser, name="register_dos_by_superuser"),
    path("superuser/register-principal/", views.register_principal_by_superuser, name="register_principal_by_superuser"),
    path("superuser/principals/<int:principal_id>/edit/", views.edit_principal_by_superuser, name="edit_principal_by_superuser"),
    path("superuser/principals/<int:principal_id>/delete/", views.delete_principal_by_superuser, name="delete_principal_by_superuser"),
    path("superuser/dos/<int:dos_id>/edit/", views.edit_dos_by_superuser, name="edit_dos_by_superuser"),
    path("superuser/dos/<int:dos_id>/delete/", views.delete_dos_by_superuser, name="delete_dos_by_superuser"),
    path("superuser/users/<int:user_id>/manual-verify/", views.manual_verify_user, name="manual_verify_user"),
    path("superuser/pending-verification/", views.pending_verification, name="pending_verification"),
    path("superuser/pending-verification/count/", views.pending_verification_count, name="pending_verification_count"),
    path("superuser/users/<int:user_id>/resend-verification/", views.resend_verification_email, name="resend_verification_email"),
    path("superuser/online-class/<int:online_class_id>/student/<int:student_id>/manual-join/", views.manual_join_online_class, name="manual_join_online_class"),

    # =====================================================
    # SCHOOL MANAGEMENT
    # =====================================================
    path("schools/add/", views.add_school, name="add_school"),
    path("schools/register/", views.register_school, name="register_school"),
    path("schools/register/success/", views.register_school_success, name="register_school_success"),
    path("schools/<int:school_id>/view/", views.view_school, name="view_school"),
    path("schools/<int:school_id>/edit/", views.edit_school, name="edit_school"),
    path("schools/<int:school_id>/activate/", views.activate_school, name="activate_school"),
    path("schools/<int:school_id>/verify/", views.activate_school, name="verify_school"),
    path("schools/verify/<str:token>/", views.verify_school_via_token, name="verify_school_via_token"),
    path("schools/<int:school_id>/deactivate/", views.deactivate_school, name="deactivate_school"),
    path("schools/<int:school_id>/delete/", views.delete_school, name="delete_school"),

    # =====================================================
    # QUERIES / MESSAGES
    # =====================================================
    path("queries/send/", views.send_query, name="send_query"),
    path("queries/<int:query_id>/reply/", views.reply_query, name="reply_query"),

    path("messages/<int:id>/reply/", views.reply_message, name="reply_message"),
    path("messages/clear-replied/", views.clear_replied_count, name="clear_replied_count"),
    path("messages/clear-all/", views.clear_all_messages, name="clear_all_messages"),
    path("messages/<int:message_id>/delete/", views.delete_single_message, name="delete_single_message"),
      path("messages/<int:message_id>/purge/", views.delete_message_completely, name="delete_message_completely"),
    path("notifications/reset/", views.reset_notification_count, name="reset_notification_count"),

    # =====================================================
    # DOS DASHBOARD
    # =====================================================
    path("dos/", views.dos_dashboard, name="dos_dashboard"),
    path("dos/open-exams/", views.open_exam_window, name="open_exam_window"),
    path("dos/close-exams/", views.close_exam_window, name="close_exam_window"),

    # =====================================================
    # VOUCHERS
    # =====================================================
    path("voucher/request/", views.request_voucher, name="request_voucher"),
    path("voucher/approve/<int:id>/",views.approve_voucher,name="approve_voucher"),
    
    # =====================================================
    # STUDENTS
    # =====================================================
    path("students/", views.manage_students, name="manage_students"),
    path("students/<int:student_id>/activate/", views.activate_student, name="activate_student"),
    path("students/<int:student_id>/deactivate/", views.deactivate_student, name="deactivate_student"),
    path("students/add/", views.add_student, name="add_student"),
    path("students/<int:student_id>/", views.view_student, name="view_student"),
    path("students/<int:student_id>/edit/", views.edit_student, name="edit_student"),
    path("students/<int:student_id>/delete/", views.delete_student, name="delete_student"),
    path("students/download/", views.download_student_list, name="download_student_list"),
    path("students/import/", views.import_students_from_excel, name="import_students_from_excel"),
    path("students/export/", views.export_students_to_excel, name="export_students_to_excel"),
    path("students/template/", views.download_student_import_template, name="download_student_import_template"),
    path("students/<int:student_id>/report/", views.student_report, name="student_report"),
    
    # API ENDPOINTS
    path("api/class-streams/", views.get_class_streams, name="get_class_streams"),

    # =====================================================
    # CLASSES
    # =====================================================
    path("classes/", views.manage_classes, name="manage_classes"),
    path("classes/list-selector/", views.class_list_selector, name="class_list_selector"),
    path("classes/add/", views.add_class, name="add_class"),
    path("classes/<int:class_id>/edit/", views.edit_class, name="edit_class"),
    path("classes/<int:class_id>/delete/", views.delete_class, name="delete_class"),
    path("classes/<int:class_id>/students/", views.view_class_students, name="view_class_students"),
    path("classes/<int:class_id>/details/", views.class_details_json, name="class_details_json"),
    path("classes/<int:class_id>/preview/", views.class_list_preview, name="class_list_preview"),
    path("classes/<int:class_id>/print/", views.print_class_list, name="print_class_list"),
    path("classes/<int:class_id>/pdf/", views.download_class_list_pdf, name="download_class_list_pdf"),
    path("classes/<int:class_id>/promote/", views.promote_class_view, name="promote_class"),
    
    # =====================================================
    # CLASS MANAGEMENT OPERATIONS
    # =====================================================
    path("classes/assign-master/", views.assign_class_master, name="assign_class_master"),
    path("classes/add-subject/", views.add_class_subject, name="add_class_subject"),
    path("classes/add-stream/", views.add_stream, name="add_stream"),
    
    # =====================================================
    # DORMITORIES
    # =====================================================
    path("dormitories/", views.manage_dorms, name="manage_dorms"),
    path("dormitories/add/", views.add_dorm, name="add_dorm"),
    path("dormitories/<int:dorm_id>/edit/", views.edit_dorm, name="edit_dorm"),
    path("dormitories/<int:dorm_id>/delete/", views.delete_dorm, name="delete_dorm"),
    path("dormitories/<int:dorm_id>/students/", views.view_dorm_students, name="view_dorm_students"),
    path("dorms/", views.dormitory_lists, name="dormitory_lists"),

    # =====================================================
    # EXAMS
    # =====================================================
    path("exams/", views.manage_exams, name="manage_exams"),
    path("exams/enter-marks/", views.enter_marks, name="enter_marks"),

    path("marksheet/full/", views.view_full_marksheet, name="view_full_marksheet"),
    path("marksheet/pdf/", views.export_marksheet_pdf, name="export_marksheet_pdf"),
    path("marksheet-center/", views.marksheet_center, name="marksheet_center"),
    path("dos/marks-hub/", views.marks_hub, name="marks_hub"),

    # =====================================================
    # REPORTS
    # =====================================================
    path("reports/", views.report_center, name="report_center"),
    path("reports/class/<int:class_id>/<int:term_id>/", views.export_class_report, name="export_class_report"),
    path("reports/class/<int:class_id>/<int:term_id>/<int:exam_id>/", views.export_class_report, name="export_class_report"),

    # =====================================================
      # =====================================================
 
    path("dos/manage-grading/", views.manage_grading, name="manage_grading"),
    path("dos/add-grading/", views.add_grading_policy, name="add_grading_policy"),
    path("dos/edit-grading/<int:grading_id>/", views.edit_grading_policy, name="edit_grading_policy"),
    path("dos/delete-grading/<int:grading_id>/", views.delete_grading_policy, name="delete_grading_policy"),

    # =====================================================
    # STUDENT AUTH
    # =====================================================
    path("student/dashboard/", views.student_dashboard, name="student_dashboard"),
    path("student/online-class/<int:online_class_id>/action/", views.student_online_class_action, name="student_online_class_action"),
    path("student/online-class/<int:online_class_id>/join/", views.student_join_online_class, name="student_join_online_class"),
    path("student/online-class/<int:online_class_id>/get-link/", views.get_online_class_meeting_link, name="get_online_class_meeting_link"),

    # =====================================================
    # PRINCIPAL
    # =====================================================
    path("principal/dashboard/", views.principal_dashboard, name="principal_dashboard"),
    path("principal/school-dos/", views.principal_school_manager, name="principal_school_manager"),
    path("principal/enter-marks/", views.enter_marks, name="enter_marks"),
    
    # =====================================================
    #TERMS
    path("terms/manage/", views.manage_terms, name="manage_terms"),
    path("terms/add/", views.add_term, name="add_term"),
    path("terms/<int:term_id>/edit/", views.edit_term, name="edit_term"),
    path("terms/<int:term_id>/delete/", views.delete_term, name="delete_term"),
    
    # =====================================================
    # NOTIFICATIONS
    path("notifications/clear/", views.clear_notifications, name="clear_notifications"),
      # Contact admin for deactivated schools (non-privileged users)
      path("contact-admin/", views.contact_admin, name="contact_admin"),
      path("contact/submit/", views.contact_submit, name="contact_submit"),
    
    # =====================================================
    # LICENSE & DEACTIVATION
    # =====================================================
    path("schools/<int:school_id>/deactivated/", views.school_deactivated, name="school_deactivated"),
    path("schools/<int:school_id>/renew-license/", views.request_license_renewal, name="request_license_renewal"),
    path("license-renewal/<int:renewal_id>/approve/", views.approve_license_renewal, name="approve_license_renewal"),
    
    # =====================================================
    # STUDENT PROMOTION
    # =====================================================
    path("promotion/center/", views.promotion_center, name="promotion_center"),
    path("promotion/class/<int:class_id>/", views.promote_class_view, name="promote_class"),
    path("promotion/student/<int:student_id>/", views.promote_student_view, name="promote_student"),
    path("promotion/school/", views.promote_school_view, name="promote_school"),
    path("promotion/history/", views.promotion_history, name="promotion_history"),
    
    # =====================================================
    # MESSAGE & NOTIFICATION MANAGEMENT
    # =====================================================
    path("messages/<int:message_id>/delete/", views.delete_message, name="delete_message"),
    path("notifications/<int:notification_id>/read/", views.mark_notification_read, name="mark_notification_read"),
    path("notifications/mark-all-read/", views.mark_all_notifications_read, name="mark_all_notifications_read"),
    
    # =====================================================
    # SCHOOL NOTICES & INFO
    # =====================================================
    path("notices/send/", views.send_school_notice, name="send_school_notice"),
    path("notices/<int:notice_id>/edit/", views.edit_notice, name="edit_notice"),
    path("notices/<int:notice_id>/followup/", views.followup_notice, name="followup_notice"),
    path("notices/<int:notice_id>/delete/", views.delete_notice, name="delete_notice"),
    path("school/edit-info/", views.edit_school_info, name="edit_school_info"),
    
]