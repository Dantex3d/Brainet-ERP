from django.urls import path
from . import views

urlpatterns = [
    path('', views.fees_dashboard, name='fees_dashboard'),
    path('structures/new/', views.create_fee_structure, name='create_fee_structure'),
    path('invoices/new/', views.create_invoice, name='create_invoice'),
    path('invoices/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:invoice_id>/receipt/', views.invoice_receipt, name='invoice_receipt'),
    path('invoices/<int:invoice_id>/pay/', views.record_payment, name='record_payment'),
    
    # Principal approval endpoints
    path('approvals/pending/', views.pending_approvals, name='pending_approvals'),
    path('structures/<int:structure_id>/approve/', views.approve_fee_structure, name='approve_fee_structure'),
    path('structures/<int:structure_id>/reject/', views.reject_fee_structure, name='reject_fee_structure'),
    path('invoices/<int:invoice_id>/approve/', views.approve_invoice, name='approve_invoice'),
    path('invoices/<int:invoice_id>/reject/', views.reject_invoice, name='reject_invoice'),
    
    # Receipt verification (public)
    path('verify/', views.verify_receipt, name='verify_receipt'),
]