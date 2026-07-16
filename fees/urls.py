from django.urls import path
from . import views


urlpatterns = [

    # Dashboard
    path(
        '',
        views.fees_dashboard,
        name='fees_dashboard'
    ),


    # Fee structures
    path(
        'structures/new/',
        views.create_fee_structure,
        name='create_fee_structure'
    ),

    path(
        'structures/<int:structure_id>/edit/',
        views.edit_fee_structure,
        name='edit_fee_structure'
    ),


    # Invoice management
    path(
        'invoices/new/',
        views.create_invoice,
        name='create_invoice'
    ),

    path(
        'invoices/<int:invoice_id>/',
        views.invoice_detail,
        name='invoice_detail'
    ),

    path(
        'invoices/<int:invoice_id>/receipt/',
        views.invoice_receipt,
        name='invoice_receipt'
    ),
    path(
        'invoices/<int:invoice_id>/receipt/pdf/',
        views.invoice_receipt_pdf,
        name='invoice_receipt_pdf'
    ),

    # Student fees
    path(
        'student-lookup/',
        views.student_lookup,
        name='student_lookup'
    ),

    path(
        'student-fees/assign/',
        views.assign_student_fee,
        name='assign_student_fee'
    ),

    # Payments
    path(
        'payments/<int:invoice_id>/record/',
        views.record_payment,
        name='record_payment'
    ),

    path(
        'payments/quick/',
        views.quick_payment,
        name='quick_payment'
    ),

    path(
        'payments/<int:payment_id>/receipt/',
        views.payment_receipt,
        name='payment_receipt'
    ),
    path(
        'payments/<int:payment_id>/receipt/pdf/',
        views.payment_receipt_pdf,
        name='payment_receipt_pdf'
    ),

    # Receipt verification
    path(
        'verify/',
        views.verify_receipt,
        name='verify_receipt'
    ),

    # Statements
    path(
        'student-statement/',
        views.student_fee_statement,
        name='student_fee_statement'
    ),
    path(
        'student-statement/pdf/',
        views.student_fee_statement_pdf,
        name='student_fee_statement_pdf'
    ),


    # Fee schedule
    path(
        'structures/schedule/',
        views.fee_structure_schedule,
        name='fee_structure_schedule'
    ),

    path(
        'structures/schedule/pdf/',
        views.fee_structure_schedule_pdf,
        name='fee_structure_schedule_pdf'
    ),


    # School payment details
    path(
        'school-payment-account/',
        views.school_payment_account,
        name='school_payment_account'
    ),


    # Receipt verification
    path(
        'verify/',
        views.verify_receipt,
        name='verify_receipt'
    ),

]