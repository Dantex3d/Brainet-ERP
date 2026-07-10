from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from schools.models import School
from .models import FeeInvoice, FeeStructure


def _can_manage_fees(user):
    return user.is_superuser or getattr(user, 'role', None) in ['principal', 'dos', 'bursar']


def _school_for_user(user):
    if user.is_superuser:
        return None
    return getattr(user, 'school', None)


@login_required
def fees_dashboard(request):
    if not _can_manage_fees(request.user):
        messages.error(request, 'You do not have access to the fees dashboard.')
        return redirect('dashboard')

    school = _school_for_user(request.user)
    structures = FeeStructure.objects.all()
    invoices = FeeInvoice.objects.all()

    if school:
        structures = structures.filter(school=school)
        invoices = invoices.filter(school=school)

    return render(request, 'fees/dashboard.html', {
        'structures': structures,
        'invoices': invoices,
        'school': school,
    })


@login_required
def create_fee_structure(request):
    # Only bursars and principals can create structures (bursars submit for principal approval)
    user_role = getattr(request.user, 'role', None)
    if user_role not in ['bursar', 'principal', 'dos'] and not request.user.is_superuser:
        messages.error(request, 'You do not have permission to create fee structures.')
        return redirect('fees_dashboard')

    school = _school_for_user(request.user)
    schools = School.objects.all() if request.user.is_superuser else [school] if school else []

    if request.method == 'POST':
        school_id = request.POST.get('school')
        selected_school = School.objects.get(id=school_id) if school_id else school
        title = request.POST.get('title', '').strip() or 'School Fees Structure'
        term = request.POST.get('term', '').strip()
        components = request.POST.get('components', '').strip()
        total_amount = request.POST.get('total_amount', '0').strip() or '0'

        fee_structure = FeeStructure.objects.create(
            school=selected_school,
            title=title,
            term=term,
            components=components,
            total_amount=total_amount,
            created_by=request.user,
        )
        messages.success(request, 'Fee structure saved successfully.')
        return redirect('fees_dashboard')

    return render(request, 'fees/fee_structure_form.html', {'schools': schools, 'school': school})


@login_required
def create_invoice(request):
    # Only bursars and principals can create invoices
    user_role = getattr(request.user, 'role', None)
    if user_role not in ['bursar', 'principal', 'dos'] and not request.user.is_superuser:
        messages.error(request, 'You do not have permission to create invoices.')
        return redirect('fees_dashboard')

    school = _school_for_user(request.user)
    schools = School.objects.all() if request.user.is_superuser else [school] if school else []
    structures = FeeStructure.objects.filter(school__in=schools, approval_status='approved') if schools else FeeStructure.objects.none()

    if request.method == 'POST':
        school_id = request.POST.get('school')
        selected_school = School.objects.get(id=school_id) if school_id else school
        payer_name = request.POST.get('payer_name', '').strip()
        description = request.POST.get('description', '').strip()
        amount = request.POST.get('amount', '0').strip() or '0'
        due_date = request.POST.get('due_date') or None
        payment_method = request.POST.get('payment_method', 'mpesa')
        structure_id = request.POST.get('structure') or None

        invoice = FeeInvoice.objects.create(
            school=selected_school,
            structure=FeeStructure.objects.get(id=structure_id) if structure_id else None,
            payer_name=payer_name,
            description=description,
            amount=amount,
            due_date=due_date,
            payment_method=payment_method,
            created_by=request.user,
        )
        messages.success(request, f'Invoice {invoice.invoice_number} created successfully.')
        return redirect('invoice_detail', invoice_id=invoice.id)

    return render(request, 'fees/invoice_form.html', {
        'schools': schools,
        'school': school,
        'structures': structures,
    })


@login_required
def invoice_detail(request, invoice_id):
    invoice = get_object_or_404(FeeInvoice, id=invoice_id)
    if not _can_manage_fees(request.user) and request.user.school != invoice.school:
        messages.error(request, 'You do not have permission to view this invoice.')
        return redirect('dashboard')

    return render(request, 'fees/invoice_detail.html', {'invoice': invoice})


@login_required
def record_payment(request, invoice_id):
    invoice = get_object_or_404(FeeInvoice, id=invoice_id)
    if not _can_manage_fees(request.user) and request.user.school != invoice.school:
        messages.error(request, 'You do not have permission to record payment for this invoice.')
        return redirect('dashboard')

    if request.method == 'POST':
        invoice.payment_method = request.POST.get('payment_method', invoice.payment_method)
        invoice.payment_reference = request.POST.get('payment_reference', invoice.payment_reference).strip()
        invoice.paid = True
        invoice.served_by = request.user
        invoice.save()
        messages.success(request, f'Payment recorded for {invoice.invoice_number}. Receipt: {invoice.receipt_number}')
        return redirect('invoice_detail', invoice_id=invoice.id)

    return render(request, 'fees/invoice_detail.html', {'invoice': invoice})


@login_required
def invoice_receipt(request, invoice_id):
    invoice = get_object_or_404(FeeInvoice, id=invoice_id)
    if not _can_manage_fees(request.user) and request.user.school != invoice.school:
        messages.error(request, 'You do not have permission to view this receipt.')
        return redirect('dashboard')

    return render(request, 'fees/receipt.html', {'invoice': invoice})


def verify_receipt(request):
    """Public receipt verification endpoint - no login required"""
    if request.method == 'POST':
        receipt_number = request.POST.get('receipt_number', '').strip().upper()
        
        try:
            invoice = FeeInvoice.objects.get(receipt_number=receipt_number, paid=True)
            return render(request, 'fees/receipt_verification_result.html', {
                'invoice': invoice,
                'valid': True,
                'message': f'Receipt {receipt_number} is valid.',
            })
        except FeeInvoice.DoesNotExist:
            return render(request, 'fees/receipt_verification_result.html', {
                'valid': False,
                'receipt_number': receipt_number,
                'message': f'Receipt {receipt_number} not found or not paid.',
            })

    return render(request, 'fees/verify_receipt.html')


@login_required
def pending_approvals(request):
    """Principal dashboard for pending fee structure and invoice approvals"""
    if getattr(request.user, 'role', None) not in ['principal', 'dos']:
        messages.error(request, 'Only principals and DOS can approve fees.')
        return redirect('dashboard')
    
    school = request.user.school
    pending_structures = FeeStructure.objects.filter(school=school, approval_status='pending')
    pending_invoices = FeeInvoice.objects.filter(school=school, approval_status='pending')
    
    return render(request, 'fees/pending_approvals.html', {
        'pending_structures': pending_structures,
        'pending_invoices': pending_invoices,
        'school': school,
    })


@login_required
def approve_fee_structure(request, structure_id):
    """Principal approves a fee structure"""
    if getattr(request.user, 'role', None) not in ['principal', 'dos']:
        messages.error(request, 'Only principals and DOS can approve fee structures.')
        return redirect('dashboard')
    
    structure = get_object_or_404(FeeStructure, id=structure_id)
    if structure.school != request.user.school:
        messages.error(request, 'You can only approve structures for your school.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        structure.approval_status = 'approved'
        structure.approved_by = request.user
        structure.approved_at = timezone.now()
        structure.save()
        messages.success(request, f'Fee structure "{structure.title}" approved successfully.')
        return redirect('pending_approvals')
    
    return render(request, 'fees/approve_structure.html', {'structure': structure})


@login_required
def reject_fee_structure(request, structure_id):
    """Principal rejects a fee structure"""
    if getattr(request.user, 'role', None) not in ['principal', 'dos']:
        messages.error(request, 'Only principals and DOS can reject fee structures.')
        return redirect('dashboard')
    
    structure = get_object_or_404(FeeStructure, id=structure_id)
    if structure.school != request.user.school:
        messages.error(request, 'You can only manage structures for your school.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        reason = request.POST.get('rejection_reason', '').strip()
        structure.approval_status = 'rejected'
        structure.rejection_reason = reason
        structure.save()
        messages.warning(request, f'Fee structure "{structure.title}" rejected.')
        return redirect('pending_approvals')
    
    return render(request, 'fees/reject_structure.html', {'structure': structure})


@login_required
def approve_invoice(request, invoice_id):
    """Principal approves a fee invoice for payment collection"""
    if getattr(request.user, 'role', None) not in ['principal', 'dos']:
        messages.error(request, 'Only principals and DOS can approve invoices.')
        return redirect('dashboard')
    
    invoice = get_object_or_404(FeeInvoice, id=invoice_id)
    if invoice.school != request.user.school:
        messages.error(request, 'You can only approve invoices for your school.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        invoice.approval_status = 'approved'
        invoice.approved_by = request.user
        invoice.approved_at = timezone.now()
        invoice.save()
        messages.success(request, f'Invoice {invoice.invoice_number} approved for {invoice.payer_name}.')
        return redirect('pending_approvals')
    
    return render(request, 'fees/approve_invoice.html', {'invoice': invoice})


@login_required
def reject_invoice(request, invoice_id):
    """Principal rejects a fee invoice"""
    if getattr(request.user, 'role', None) not in ['principal', 'dos']:
        messages.error(request, 'Only principals and DOS can reject invoices.')
        return redirect('dashboard')
    
    invoice = get_object_or_404(FeeInvoice, id=invoice_id)
    if invoice.school != request.user.school:
        messages.error(request, 'You can only manage invoices for your school.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        reason = request.POST.get('rejection_reason', '').strip()
        invoice.approval_status = 'rejected'
        invoice.rejection_reason = reason
        invoice.save()
        messages.warning(request, f'Invoice {invoice.invoice_number} rejected.')
        return redirect('pending_approvals')
    
    return render(request, 'fees/reject_invoice.html', {'invoice': invoice})
