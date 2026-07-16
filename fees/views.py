from decimal import Decimal
from datetime import date
import math
import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.http import HttpResponse

from io import BytesIO
from urllib.request import urlopen
from urllib.parse import urlparse
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet

from schools.models import School, Term
from students.models import Student

from .models import (
    FeeInvoice,
    FeeLedger,
    FeePayment,
    FeeStructure,
    StudentFeeAccount,
)


@login_required
def quick_payment(request):
    """Record a payment by student's admission number.

    Uses the student's fee account and any existing fee structure for the selected term
    so balances are derived from the fee structure, not from an invoice.
    """
    school = get_school(request.user)
    terms = Term.objects.filter(school=school) if school else Term.objects.none()

    if request.method == 'POST':
        admission_number = request.POST.get('admission_number', '').strip()
        amount = parse_decimal(request.POST.get('amount'))
        payment_method = request.POST.get('payment_method', 'cash')
        payment_reference = request.POST.get('payment_reference', '').strip()
        term_value = request.POST.get('term', '').strip()

        if not admission_number:
            messages.error(request, 'Admission number is required.')
            return redirect('quick_payment')

        if amount <= Decimal('0'):
            messages.error(request, 'Amount must be greater than zero.')
            return redirect('quick_payment')

        student = Student.objects.filter(admission_number__iexact=admission_number).first()
        if not student:
            messages.error(request, 'Student not found.')
            return redirect('quick_payment')

        if not term_value:
            current = current_term(student.school)
            term_value = current.name if current else ''

        academic_year = str(timezone.now().year)
        structure = FeeStructure.objects.filter(
            school=student.school,
            term=term_value,
        ).order_by("-academic_year").first()

        if not structure:
            structure = FeeStructure.objects.filter(
                school=student.school,
                academic_year=academic_year,
                term__exact="",
            ).order_by("-academic_year").first()

        if structure:
            academic_year = structure.academic_year
            split = structure.split_term_amounts()
            charge_amount = split.get(term_value, structure.total_amount)
        else:
            charge_amount = Decimal('0')

        account = StudentFeeAccount.objects.filter(
            student=student,
            school=student.school,
            academic_year=academic_year,
            term=term_value,
        ).first()

        if not account:
            account = create_student_fee_account(
                student=student,
                school=student.school,
                academic_year=academic_year,
                term=term_value,
                amount=charge_amount,
            )
        elif structure:
            desired_amount = split.get(term_value, structure.total_amount)
            if account.fees_charged != desired_amount:
                account.fees_charged = desired_amount
                account.save()

        if payment_reference:
            existing_payment = FeePayment.objects.filter(
                reference__iexact=payment_reference,
            ).first()
            if existing_payment:
                messages.warning(request, 'Duplicate payment reference detected. Showing existing receipt.')
                return redirect('payment_receipt', payment_id=existing_payment.pk)

        payment = FeePayment.objects.create(
            account=account,
            invoice=None,
            amount=amount,
            payment_method=payment_method,
            reference=payment_reference,
            received_by=request.user,
        )

        account.last_payment_date = timezone.now()
        account.save()

        messages.success(request, f'Payment recorded. Receipt: {payment.receipt_number}')
        return redirect('payment_receipt_pdf', payment_id=payment.pk)

    return render(request, 'fees/quick_payment.html', {
        'school': school,
        'terms': terms,
    })


@login_required
def payment_receipt(request, payment_id):
    payment = get_object_or_404(FeePayment, pk=payment_id)
    account = payment.account
    student = account.student if account else None
    term_name = account.term if account else ''
    current_balance = account.closing_balance if account else Decimal('0')
    paid_amount = payment.amount
    if payment.received_by:
        served_by_name = payment.received_by.get_name() if hasattr(payment.received_by, 'get_name') else (payment.received_by.get_full_name() or getattr(payment.received_by, 'username', ''))
    else:
        served_by_name = request.user.get_name() if hasattr(request.user, 'get_name') else (request.user.get_full_name() or getattr(request.user, 'username', ''))

    fee_structure = None
    annual_amount = None
    term_amount = None
    overall_balance = current_balance
    if account and student:
        fee_structure = FeeStructure.objects.filter(
            school=student.school,
            academic_year=account.academic_year,
            term=term_name,
        ).first()
        if not fee_structure:
            fee_structure = FeeStructure.objects.filter(
                school=student.school,
                academic_year=account.academic_year,
            ).first()

        term_history, total_expected, total_paid_year, total_unpaid, allocations = _get_student_term_allocations(student)
        term_allocation = allocations.get(account.pk)
        if term_allocation is not None:
            current_balance = term_allocation['balance']
        overall_balance = total_expected - total_paid_year

    balance_amount = current_balance

    return render(request, 'fees/payment_receipt.html', {
        'payment': payment,
        'account': account,
        'student': student,
        'term_name': term_name,
        'fee_structure': fee_structure,
        'annual_amount': annual_amount,
        'term_amount': term_amount,
        'balance_amount': current_balance,
        'current_balance': current_balance,
        'overall_balance': overall_balance,
        'paid_amount': paid_amount,
        'served_by_name': served_by_name,
        'amount_in_words': amount_to_words(payment.amount),
    })


def can_manage_fees(user):
    return (
        user.is_superuser or
        getattr(user, "role", "").lower() in [
            "principal",
            "bursar",
            "dos",
        ]
    )


def get_school(user):
    if user.is_superuser:
        return None
    return getattr(user, "school", None)


def current_term(school):
    if school is None:
        return None

    today = timezone.now().date()
    term = Term.objects.filter(
        school=school,
        start_date__lte=today,
        end_date__gte=today,
    ).first()

    if not term:
        term = Term.objects.filter(school=school).order_by("-start_date").first()

    return term


def next_term(school):
    if school is None:
        return None
    today = timezone.now().date()
    return Term.objects.filter(school=school, start_date__gt=today).order_by("start_date").first()


def parse_decimal(value, default=Decimal("0")):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except Exception:
        return default


def number_to_words(number: int) -> str:
    if number == 0:
        return "zero"

    units = [
        "", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
        "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
        "seventeen", "eighteen", "nineteen",
    ]
    tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
    scales = ["", "thousand", "million", "billion", "trillion"]

    words = []

    def _split_by_thousands(n):
        while n > 0:
            n, remainder = divmod(n, 1000)
            yield remainder

    def _three_digit_word(n):
        hundred, remainder = divmod(n, 100)
        result = []
        if hundred:
            result.append(units[hundred])
            result.append("hundred")
        if remainder:
            if remainder < 20:
                result.append(units[remainder])
            else:
                ten, unit = divmod(remainder, 10)
                result.append(tens[ten])
                if unit:
                    result.append(units[unit])
        return result

    for idx, chunk in enumerate(_split_by_thousands(number)):
        if chunk:
            chunk_words = _three_digit_word(chunk)
            if scales[idx]:
                chunk_words.append(scales[idx])
            words.insert(0, " ".join(chunk_words))

    return ", ".join(words).strip()


def amount_to_words(amount: Decimal) -> str:
    integer_part = int(math.floor(amount))
    fractional_part = int((amount - integer_part) * 100)
    words = number_to_words(integer_part).title()
    if fractional_part:
        words += f" and {fractional_part:02d}/100"
    return words + " shillings only"


def _get_term_order_for_school(school):
    if not school:
        return {}
    term_names = list(
        Term.objects.filter(school=school)
        .order_by("start_date")
        .values_list("name", flat=True)
        .distinct()
    )
    return {name: idx for idx, name in enumerate(term_names)}


def _sort_student_accounts(student, accounts):
    term_order = _get_term_order_for_school(student.school)

    def sort_key(account):
        academic_year_key = account.academic_year
        try:
            academic_year_key = int(str(account.academic_year))
        except Exception:
            pass
        term_index = term_order.get(account.term, 999)
        return (academic_year_key, term_index, account.term or "")

    return sorted(accounts, key=sort_key)


def _allocate_student_payments(accounts, total_paid):
    remaining_paid = total_paid
    total_expected = Decimal("0")
    term_history = []
    allocations = {}

    for account in accounts:
        expected = account.opening_balance + account.fees_charged
        allocated_paid = min(expected, remaining_paid) if remaining_paid > 0 else Decimal("0")
        remaining_paid -= allocated_paid
        unpaid = expected - allocated_paid
        allocation = {
            "term": account.term or "Unknown",
            "expected": expected,
            "paid": allocated_paid,
            "unpaid": unpaid,
            "balance": unpaid,
            "academic_year": account.academic_year,
            "account": account,
        }
        term_history.append(allocation)
        allocations[account.pk] = allocation
        total_expected += expected

    total_unpaid = sum(item["unpaid"] for item in term_history)
    return term_history, total_expected, total_unpaid, allocations


def _get_student_term_allocations(student, total_paid=None):
    if total_paid is None:
        total_paid = FeePayment.objects.filter(account__student=student).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    accounts = StudentFeeAccount.objects.filter(student=student)
    ordered_accounts = _sort_student_accounts(student, accounts)
    term_history, total_expected, total_unpaid, allocations = _allocate_student_payments(ordered_accounts, total_paid)
    return term_history, total_expected, total_paid, total_unpaid, allocations


def get_student_statement(student):
    invoices = FeeInvoice.objects.filter(student=student).order_by("generated_at")
    payments = FeePayment.objects.filter(account__student=student).order_by("date_paid")
    accounts = StudentFeeAccount.objects.filter(student=student).order_by("academic_year", "term")
    term_history = []

    total_expected = Decimal("0")
    total_paid = payments.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    total_unpaid = Decimal("0")
    allocations = {}

    structure_total = Decimal("0")
    if accounts.exists():
        ordered_accounts = _sort_student_accounts(student, accounts)
        term_history, total_expected, total_unpaid, allocations = _allocate_student_payments(ordered_accounts, total_paid)

        academic_years = ordered_accounts and list({account.academic_year for account in ordered_accounts}) or []
        if academic_years and student.school:
            structures = FeeStructure.objects.filter(school=student.school, academic_year__in=academic_years)
            for year in academic_years:
                year_structures = structures.filter(academic_year=year)
                if year_structures.exists():
                    year_blank = year_structures.filter(term="").first()
                    if year_blank:
                        structure_total += year_blank.total_amount
                    else:
                        structure_total += year_structures.aggregate(total=Sum("total_amount"))["total"] or Decimal("0")
        if structure_total > total_expected:
            total_expected = structure_total
    else:
        invoices_by_term = {}
        for invoice in invoices:
            term = invoice.term or "Unknown"
            term_data = invoices_by_term.setdefault(term, {"expected": Decimal("0"), "paid": Decimal("0")})
            term_data["expected"] += invoice.amount
            if invoice.paid:
                term_data["paid"] += invoice.amount
        for term, data in invoices_by_term.items():
            unpaid = max(data["expected"] - data["paid"], Decimal("0"))
            term_history.append({
                "term": term,
                "expected": data["expected"],
                "paid": data["paid"],
                "unpaid": unpaid,
                "balance": unpaid,
            })
            total_expected += data["expected"]
            total_unpaid += unpaid

    accumulated_debt = total_unpaid
    current_balance = total_expected - total_paid
    annual_debt = total_expected - total_paid
    total_payments = payments.count()
    last_payment_date = payments.last().date_paid if payments.exists() else None

    payment_history = []
    running_paid = Decimal("0")
    for payment in payments:
        running_paid += payment.amount
        balance_after = total_expected - running_paid
        if payment.received_by:
            served_by_text = payment.received_by.get_name() if hasattr(payment.received_by, 'get_name') else (payment.received_by.get_full_name() or getattr(payment.received_by, 'username', None))
            served_by_text = served_by_text or "System"
        else:
            served_by_text = "System"

        payment_history.append({
            "date": payment.date_paid,
            "amount": payment.amount,
            "method": payment.get_payment_method_display(),
            "reference": payment.reference or "-",
            "served_by": served_by_text,
            "term": payment.account.term or "N/A",
            "invoice": payment.invoice.receipt_number if payment.invoice else "Quick Pay",
            "receipt_url": reverse("invoice_receipt_pdf", kwargs={"invoice_id": payment.invoice.pk}) if payment.invoice else None,
            "balance_after": balance_after,
        })

    return {
        "student": student,
        "school": student.school,
        "invoice_history": invoices,
        "payment_history": payment_history,
        "term_history": term_history,
        "total_expected": total_expected,
        "total_paid": total_paid,
        "total_unpaid": total_unpaid,
        "total_payments": total_payments,
        "last_payment_date": last_payment_date,
        "accumulated_debt": accumulated_debt,
        "current_balance": current_balance,
        "annual_debt": annual_debt,
        "academic_year": str(timezone.now().year),
        "annual_debt": annual_debt,
        "academic_year": str(timezone.now().year),
    }


def create_student_fee_account(student, school, academic_year, term, amount):
    account, created = StudentFeeAccount.objects.get_or_create(
        student=student,
        school=school,
        academic_year=academic_year,
        term=term,
        defaults={
            "opening_balance": Decimal("0"),
            "fees_charged": amount,
            "closing_balance": amount,
        },
    )
    if not created and amount > Decimal('0') and account.fees_charged != amount:
        account.fees_charged = amount
        account.save()
    return account


@login_required
def fees_dashboard(request):
    if not can_manage_fees(request.user):
        messages.error(request, "Permission denied.")
        return redirect("dashboard")

    school = get_school(request.user)

    structures = FeeStructure.objects.all()
    invoices = FeeInvoice.objects.filter(paid=False)
    accounts = StudentFeeAccount.objects.all()
    payments = FeePayment.objects.all()

    if school:
        structures = structures.filter(school=school)
        invoices = invoices.filter(school=school)
        accounts = accounts.filter(student__school=school)
        payments = payments.filter(account__student__school=school)

    total_expected = structures.aggregate(total=Sum("total_amount"))["total"] or Decimal("0")
    total_paid = payments.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    total_balance = accounts.aggregate(total=Sum("closing_balance"))["total"] or Decimal("0")

    context = {
        "school": school,
        "structures": structures,
        "invoices": invoices.order_by("-generated_at")[:10],
        "students": accounts.count(),
        "payments": payments.count(),
        "total_expected": total_expected,
        "total_paid": total_paid,
        "total_balance": total_balance,
    }
    return render(request, "fees/dashboard.html", context)


@login_required
def student_lookup(request):
    admission_number = request.GET.get("admission_number", "").strip()
    if not admission_number:
        return JsonResponse({"ok": False, "message": "Admission number is required."}, status=400)

    student = Student.objects.filter(admission_number__iexact=admission_number).first()
    if not student:
        return JsonResponse({"ok": False, "message": "Student not found."}, status=404)

    return JsonResponse({
        "ok": True,
        "student": {
            "id": student.pk,
            "name": student.name,
            "admission_number": student.admission_number,
            "gender": student.gender,
            "school": {
                "id": student.school.id,
                "name": student.school.name,
            },
            "class": student.current_class.name if student.current_class else None,
            "stream": student.stream.name if student.stream else None,
            "parent_phone": student.parent_phone,
            "status": student.status,
        },
    })


@login_required
def create_invoice(request):
    school = get_school(request.user)
    schools = School.objects.all() if request.user.is_superuser else []
    structures = FeeStructure.objects.all()
    terms = Term.objects.filter(school=school) if school else Term.objects.none()
    current = current_term(school)

    if request.method == "POST":
        school_id = request.POST.get("school")
        if request.user.is_superuser and school_id:
            school = get_object_or_404(School, pk=school_id)
        if not school:
            return HttpResponseBadRequest("School must be selected.")

        structure_id = request.POST.get("structure")
        structure = FeeStructure.objects.filter(pk=structure_id, school=school).first() if structure_id else None
        term_value = request.POST.get("term") or (structure.term if structure else "")
        admission_number = request.POST.get("admission_number", "").strip()
        student = Student.objects.filter(admission_number__iexact=admission_number).first() if admission_number else None
        payer_name = request.POST.get("payer_name", "").strip()
        description = request.POST.get("description", "").strip()
        amount = parse_decimal(request.POST.get("amount"))
        due_date = request.POST.get("due_date") or None
        payment_method = request.POST.get("payment_method", "cash")

        if structure and amount == 0:
            amount = structure.total_amount
            if term_value and term_value in structure.split_term_amounts():
                amount = structure.split_term_amounts()[term_value]

        if not payer_name:
            payer_name = student.name if student else "Unknown"

        invoice = FeeInvoice.objects.create(
            school=school,
            account=None,
            structure=structure,
            student=student,
            payer_name=payer_name,
            description=description,
            amount=amount,
            due_date=due_date or None,
            payment_method=payment_method,
            created_by=request.user,
        )

        if student:
            academic_year = structure.academic_year if structure else (timezone.now().year if not term_value else str(timezone.now().year))
            account = create_student_fee_account(
                student=student,
                school=school,
                academic_year=academic_year,
                term=term_value,
                amount=amount,
            )
            invoice.account = account
            invoice.save()

        messages.success(request, "Invoice created successfully.")
        return redirect("invoice_detail", invoice_id=invoice.pk)

    context = {
        "school": school,
        "schools": schools,
        "structures": structures.filter(school=school) if school else structures,
        "terms": terms,
        "current_term": current,
        "selected_school": school,
    }
    return render(request, "fees/invoice_form.html", context)


@login_required
def invoice_detail(request, invoice_id):
    invoice = get_object_or_404(FeeInvoice, pk=invoice_id)
    statement = None
    if invoice.student:
        statement = get_student_statement(invoice.student)

    return render(request, "fees/invoice_detail.html", {
        "invoice": invoice,
        "statement": statement,
    })


@login_required
def invoice_receipt(request, invoice_id):
    invoice = get_object_or_404(FeeInvoice, pk=invoice_id)
    total_paid = FeePayment.objects.filter(invoice=invoice).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    invoice_balance = invoice.amount - total_paid
    context = {
        "invoice": invoice,
        "invoice_balance": invoice_balance,
        "amount_paid": total_paid,
        "amount_in_words": amount_to_words(invoice.amount),
        "structure_total": invoice.structure.total_amount if invoice.structure else None,
    }

    # Term specific balances
    student = invoice.student
    if student:
        term_name = invoice.term or ''
        year_term_history, year_total_expected, year_total_paid, year_total_unpaid, allocations = _get_student_term_allocations(student)
        term_balance = Decimal('0')
        term_due = Decimal('0')
        term_paid = Decimal('0')

        if invoice.account:
            allocation = allocations.get(invoice.account.pk)
            if allocation:
                term_due = allocation['expected']
                term_paid = allocation['paid']
                term_balance = allocation['balance']
        elif term_name:
            term_accounts = StudentFeeAccount.objects.filter(student=student, term=term_name)
            for acc in term_accounts:
                allocation = allocations.get(acc.pk)
                if allocation:
                    term_due += allocation['expected']
                    term_paid += allocation['paid']
                    term_balance += allocation['balance']
                else:
                    term_due += acc.opening_balance + acc.fees_charged
                    paid = FeePayment.objects.filter(account=acc).aggregate(total=Sum("amount"))["total"] or Decimal('0')
                    term_paid += paid
                    term_balance += term_due - paid

        nxt = next_term(student.school)
        next_name = nxt.name if nxt else ''
        next_term_balance = Decimal('0')
        if next_name:
            next_accounts = StudentFeeAccount.objects.filter(student=student, term=next_name)
            for acc in next_accounts:
                next_term_balance += allocations.get(acc.pk, {}).get('balance', acc.opening_balance + acc.fees_charged - acc.total_paid)

        overall_balance = year_total_expected - year_total_paid

        context.update({
            'term_name': term_name,
            'term_due': term_due,
            'term_paid': term_paid,
            'term_balance': term_balance,
            'next_term_name': next_name,
            'next_term_balance': next_term_balance,
            'overall_balance': overall_balance,
        })

    context['overall_balance'] = overall_balance
    return render(request, "fees/receipt.html", context)


@login_required
def invoice_receipt_pdf(request, invoice_id):
    invoice = get_object_or_404(FeeInvoice, pk=invoice_id)
    total_paid = FeePayment.objects.filter(invoice=invoice).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    invoice_balance = invoice.amount - total_paid

    term_name = invoice.term or ''
    student = invoice.student
    term_balance = Decimal('0')
    next_term_name = ''
    next_term_balance = Decimal('0')

    if student:
        student_total_paid = FeePayment.objects.filter(account__student=student).aggregate(total=Sum("amount"))["total"] or Decimal('0')
        term_history, total_expected, total_paid_year, total_unpaid, allocations = _get_student_term_allocations(student, student_total_paid)
        if invoice.account:
            term_balance = allocations.get(invoice.account.pk, {}).get('balance', invoice.account.opening_balance + invoice.account.fees_charged - invoice.account.total_paid)
        else:
            term_balance = Decimal('0')
        nxt = next_term(student.school)
        next_term_name = nxt.name if nxt else ''
        if next_term_name:
            next_accounts = StudentFeeAccount.objects.filter(student=student, term=next_term_name)
            next_term_balance = sum(allocations.get(acc.pk, {}).get('balance', acc.opening_balance + acc.fees_charged - acc.total_paid) for acc in next_accounts)
        else:
            next_term_balance = Decimal('0')
        overall_balance = total_expected - total_paid_year
    structure_total = invoice.structure.total_amount if invoice.structure else None

    school = invoice.school
    watermark_logo = _load_reportlab_logo(getattr(school, 'logo', None), width=40*mm, height=40*mm) if school else None
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=(148*mm, 210*mm),
        leftMargin=10*mm,
        rightMargin=10*mm,
        topMargin=10*mm,
        bottomMargin=10*mm,
    )
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    normal.leading = 14
    title_style = styles["Title"]
    title_style.fontSize = 16
    title_style.alignment = 1
    elements = []

    header_html = []
    if school:
        if school.name:
            header_html.append(f"<b>{school.name}</b>")
        if school.address:
            header_html.append(school.address)
        contact = []
        if school.phone:
            contact.append(f"Tel: {school.phone}")
        if school.email:
            contact.append(f"Email: {school.email}")
        if contact:
            header_html.append(' • '.join(contact))
    else:
        header_html.append("Official Payment Receipt")

    logo = _load_reportlab_logo(getattr(school, 'logo', None), width=25*mm, height=25*mm) if school else None
    header_cells = [logo if logo else '', Paragraph('<br/>'.join(header_html), normal)]
    header_table = Table([header_cells], colWidths=[30*mm, doc.width - 30*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LINEBELOW', (0,0), (-1,0), 1.5, colors.HexColor('#163b7d')),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 10))
    elements.append(Paragraph('OFFICIAL PAYMENT RECEIPT', title_style))
    elements.append(Spacer(1, 8))

    info_data = [
        ['Receipt Number', invoice.receipt_number or invoice.invoice_number],
        ['Date', invoice.generated_at.strftime('%d %b %Y %H:%M') if invoice.generated_at else ''],
        ['Student', invoice.student.name if invoice.student else invoice.payer_name],
        ['Admission No', invoice.student.admission_number if invoice.student else '-'],
        ['Class / Stream', f"{invoice.student.current_class.name if invoice.student and invoice.student.current_class else '-'}{(' / ' + invoice.student.stream.name) if invoice.student and invoice.student.stream else ''}"],
        ['Term', term_name or 'N/A'],
    ]
    info_table = Table(info_data, colWidths=[45*mm, doc.width - 45*mm])
    info_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.grey),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f4f7fb')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 10))

    summary_data = [
        ['Invoice Amount', f"KES {invoice.amount:,.2f}"],
        ['Amount Paid', f"KES {total_paid:,.2f}"],
        ['Invoice Balance', f"KES {invoice_balance:,.2f}"],
        ['Term Balance', f"KES {term_balance:,.2f}"],
    ]
    if structure_total is not None:
        summary_data.insert(1, ['Full Fee Structure Total', f"KES {structure_total:,.2f}"])
    if next_term_name:
        summary_data.append([f"Next Term ({next_term_name}) Balance", f"KES {next_term_balance:,.2f}"])
    summary_table = Table(summary_data, colWidths=[65*mm, doc.width - 65*mm])
    summary_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.grey),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#163b7d')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"Amount in Words: {amount_to_words(invoice.amount)}", normal))
    elements.append(Spacer(1, 12))
    footer_text = "Official receipt generated by Brainet ERP. Keep this receipt for your records. Payments to unofficial accounts are not supported."
    elements.append(Paragraph(footer_text, normal))

    doc.build(elements, onFirstPage=lambda canvas, doc: _draw_reportlab_watermark(canvas, doc, school.name if school else 'Brainet ERP', watermark_logo))
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="payment_receipt.pdf"'
    return response


@login_required
def payment_receipt_pdf(request, payment_id):
    payment = get_object_or_404(FeePayment, pk=payment_id)
    account = payment.account
    student = account.student if account else None
    term_name = account.term if account else ''
    account_balance = account.closing_balance if account else Decimal('0')
    current_balance = account_balance
    paid_amount = payment.amount
    if payment.received_by:
        served_by_name = payment.received_by.get_name() if hasattr(payment.received_by, 'get_name') else (payment.received_by.get_full_name() or getattr(payment.received_by, 'username', '') or (payment.received_by.get_username() if hasattr(payment.received_by, 'get_username') else ''))
    elif request.user.is_authenticated:
        served_by_name = request.user.get_name() if hasattr(request.user, 'get_name') else (request.user.get_full_name() or getattr(request.user, 'username', '') or (request.user.get_username() if hasattr(request.user, 'get_username') else ''))
    else:
        served_by_name = 'System'

    if not served_by_name:
        served_by_name = 'System'

    overall_balance = account.closing_balance if account else Decimal('0')
    if student and account:
        term_history, total_expected, total_paid_year, total_unpaid, allocations = _get_student_term_allocations(student)
        overall_balance = total_expected - total_paid_year
        current_balance = allocations.get(account.pk, {}).get('balance', current_balance)
    else:
        current_balance = current_balance

    school = account.school if account else None
    overall_balance = account_balance
    if account and student:
        student_total_paid = FeePayment.objects.filter(account__student=student).aggregate(total=Sum("amount"))["total"] or Decimal('0')
        term_history, total_expected_year, total_paid_year, total_unpaid, allocations = _get_student_term_allocations(student, student_total_paid)
        current_balance = allocations.get(account.pk, {}).get('balance', account_balance)
        overall_balance = total_expected_year - total_paid_year

    watermark_logo = _load_reportlab_logo(getattr(school, 'logo', None), width=40*mm, height=40*mm) if school else None
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=(148*mm, 210*mm),
        leftMargin=10*mm,
        rightMargin=10*mm,
        topMargin=10*mm,
        bottomMargin=10*mm,
    )
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    normal.leading = 14
    title_style = styles["Title"]
    title_style.fontSize = 16
    title_style.alignment = 1
    elements = []

    header_html = []
    if school:
        if school.name:
            header_html.append(f"<b>{school.name}</b>")
        if school.address:
            header_html.append(school.address)
        contact = []
        if school.phone:
            contact.append(f"Tel: {school.phone}")
        if school.email:
            contact.append(f"Email: {school.email}")
        if contact:
            header_html.append(' • '.join(contact))
    else:
        header_html.append("Official Payment Receipt")

    logo = _load_reportlab_logo(getattr(school, 'logo', None), width=25*mm, height=25*mm) if school else None
    header_cells = [logo if logo else '', Paragraph('<br/>'.join(header_html), normal)]
    header_table = Table([header_cells], colWidths=[30*mm, doc.width - 30*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LINEBELOW', (0,0), (-1,0), 1.5, colors.HexColor('#163b7d')),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 10))
    elements.append(Paragraph('OFFICIAL PAYMENT RECEIPT', title_style))
    elements.append(Spacer(1, 8))

    info_data = [
        ['Receipt Number', payment.receipt_number],
        ['Date', payment.date_paid.strftime('%d %b %Y %H:%M') if payment.date_paid else ''],
        ['Student', student.name if student else '-'],
        ['Admission No', student.admission_number if student else '-'],
        ['Class / Stream', f"{student.current_class.name if student and student.current_class else '-'}{(' / ' + student.stream.name) if student and student.stream else ''}"],
        ['Term', term_name or 'N/A'],
        ['Payment Method', payment.get_payment_method_display()],
        ['Reference', payment.reference or '-'],
        ['Saved By', served_by_name],
    ]
    info_table = Table(info_data, colWidths=[45*mm, doc.width - 45*mm])
    info_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.grey),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f4f7fb')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 10))

    summary_data = [
        ['Paid Amount', f"KES {paid_amount:,.2f}"],
        ['Term Balance', f"KES {current_balance:,.2f}"],
        ['Overall Year Balance', f"KES {overall_balance:,.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[65*mm, doc.width - 65*mm])
    summary_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.grey),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#163b7d')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"Amount in Words: {amount_to_words(payment.amount)}", normal))
    elements.append(Spacer(1, 12))
    footer_text = "Official receipt generated by Brainet ERP. Keep this receipt for your records. Payments to unofficial accounts are not supported."
    elements.append(Paragraph(footer_text, normal))

    doc.build(elements, onFirstPage=lambda canvas, doc: _draw_reportlab_watermark(canvas, doc, school.name if school else 'Brainet ERP', watermark_logo))
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="payment_receipt.pdf"'
    return response


@login_required
def record_payment(request, invoice_id):
    invoice = get_object_or_404(FeeInvoice, pk=invoice_id)
    if request.method != "POST":
        return HttpResponseBadRequest("Payment must be posted.")
    if invoice.paid:
        return JsonResponse({"ok": False, "message": "Invoice is already paid."}, status=400)

    payment_method = request.POST.get("payment_method", "cash")
    payment_reference = request.POST.get("payment_reference", "").strip()
    invoice.mark_paid(payment_method=payment_method, payment_reference=payment_reference, served_by=request.user)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        receipt_url = request.build_absolute_uri(reverse("invoice_receipt_pdf", kwargs={"invoice_id": invoice.pk}))
        return JsonResponse({
            "ok": True,
            "message": "Payment recorded successfully.",
            "receipt_number": invoice.receipt_number,
            "receipt_url": receipt_url,
        })
    messages.success(request, "Payment recorded and receipt generated.")
    return redirect("invoice_detail", invoice_id=invoice.pk)


@login_required
def assign_student_fee(request):
    messages.info(request, "Student fee assignment page is not yet implemented.")
    return redirect("fees_dashboard")


@login_required
def student_fee_statement(request):
    admission_number = request.GET.get("admission_number", "").strip()
    statement = None
    school = get_school(request.user)
    student = None

    if not admission_number and getattr(request.user, 'role', None) == 'student':
        student = Student.objects.filter(user=request.user).first()
        if student:
            admission_number = student.admission_number

    if admission_number:
        student = Student.objects.filter(admission_number__iexact=admission_number).first()
        if student:
            statement = get_student_statement(student)

    return render(request, "fees/student_fee_statement.html", {
        "admission_number": admission_number,
        "statement": statement,
    })


@login_required
def student_fee_statement_pdf(request):
    admission_number = request.GET.get("admission_number", "").strip()
    if not admission_number and getattr(request.user, 'role', None) == 'student':
        student = Student.objects.filter(user=request.user).first()
        if student:
            admission_number = student.admission_number

    if not admission_number:
        return HttpResponseBadRequest("Admission number is required.")

    student = Student.objects.filter(admission_number__iexact=admission_number).first()
    if not student:
        return HttpResponseBadRequest("Student not found.")

    statement = get_student_statement(student)

    school = student.school
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=12*mm,
        rightMargin=12*mm,
        topMargin=12*mm,
        bottomMargin=12*mm,
    )
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    normal.leading = 14
    title_style = styles["Title"]
    title_style.fontSize = 16
    title_style.alignment = 1
    elements = []

    header_html = []
    if school:
        header_html.append(f"<b>{school.name}</b>")
        if school.address:
            header_html.append(school.address)
        contact = []
        if school.phone:
            contact.append(f"Tel: {school.phone}")
        if school.email:
            contact.append(f"Email: {school.email}")
        if contact:
            header_html.append(' • '.join(contact))
    else:
        header_html.append("Student Fee Statement")

    logo = _load_reportlab_logo(getattr(school, 'logo', None), width=25*mm, height=25*mm) if school else None
    header_cells = [logo if logo else '', Paragraph('<br/>'.join(header_html), normal)]
    header_table = Table([header_cells], colWidths=[30*mm, doc.width - 30*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LINEBELOW', (0,0), (-1,0), 1.5, colors.HexColor('#163b7d')),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 10))
    elements.append(Paragraph('STUDENT FEE STATEMENT', title_style))
    elements.append(Spacer(1, 8))

    student_info = [
        ['Student', student.name],
        ['Admission No', student.admission_number],
        ['Class / Stream', f"{student.current_class.name if student.current_class else '-'}{(' / ' + student.stream.name) if student.stream else ''}"],
        ['Academic Year', statement['academic_year']],
    ]
    student_table = Table(student_info, colWidths=[45*mm, doc.width - 45*mm])
    student_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.4, colors.grey),
        ('INNERGRID', (0,0), (-1,-1), 0.4, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f4f7fb')),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
    ]))
    elements.append(student_table)
    elements.append(Spacer(1, 10))

    summary_data = [
        ['Total Expected Fees', f"KES {statement['total_expected']:,.2f}"],
        ['Total Paid', f"KES {statement['total_paid']:,.2f}"],
        ['Current Balance', f"KES {statement['current_balance']:,.2f}"],
        ['Annual Debt', f"KES {statement['annual_debt']:,.2f}"],
        ['Term Unpaid Total', f"KES {statement['accumulated_debt']:,.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[55*mm, doc.width - 55*mm])
    summary_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.4, colors.grey),
        ('INNERGRID', (0,0), (-1,-1), 0.4, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#163b7d')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        'Note: Payments are allocated across earlier, current, and next term accounts in chronological order. Sufficient payments can reduce the current term balance to KES 0.00 when the student has overpaid for the year.',
        normal
    ))
    elements.append(Spacer(1, 10))

    payment_history_data = [[
        'Date', 'Amount', 'Method', 'Reference', 'Term', 'Receipt', 'Balance After'
    ]]
    for payment in statement['payment_history']:
        payment_history_data.append([
            payment['date'].strftime('%d %b %Y %H:%M') if payment['date'] else '',
            f"KES {payment['amount']:,.2f}",
            payment['method'],
            payment['reference'],
            payment['term'],
            payment['invoice'],
            f"KES {payment['balance_after']:,.2f}",
        ])

    payment_history_table = Table(payment_history_data, colWidths=[30*mm, 24*mm, 32*mm, 32*mm, 18*mm, 28*mm, 22*mm])
    payment_history_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.35, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f4f7fb')),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))

    elements.append(Paragraph('Payment History', styles['Heading3']))
    elements.append(Spacer(1, 6))
    elements.append(payment_history_table)
    elements.append(Spacer(1, 10))

    processed_by_data = [[
        'Receipt', 'Processed By'
    ]]
    for payment in statement['payment_history']:
        processed_by_data.append([
            payment['invoice'],
            payment['served_by'],
        ])

    processed_by_table = Table(processed_by_data, colWidths=[45*mm, doc.width - 45*mm])
    processed_by_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.35, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f4f7fb')),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))

    elements.append(Paragraph('Processed By', styles['Heading3']))
    elements.append(Spacer(1, 6))
    elements.append(processed_by_table)
    elements.append(Spacer(1, 10))
    footer_text = "This statement is generated by Brainet ERP. Please keep it for your records and verify payments against official school accounts."
    elements.append(Paragraph(footer_text, normal))

    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="student_fee_statement.pdf"'
    return response


@login_required
def create_fee_structure(request):
    school = get_school(request.user)
    schools = School.objects.all() if request.user.is_superuser else []
    structure = None

    if request.method == "POST":
        school_id = request.POST.get("school")
        if request.user.is_superuser and school_id:
            school = get_object_or_404(School, pk=school_id)
        if not school:
            return HttpResponseBadRequest("School must be selected.")

        title = request.POST.get("title", "").strip()
        term = request.POST.get("term", "").strip()
        components = request.POST.get("components", "").strip()
        total_amount = parse_decimal(request.POST.get("total_amount"))
        term1_percentage = int(request.POST.get("term1_percentage", 0) or 0)
        term2_percentage = int(request.POST.get("term2_percentage", 0) or 0)
        term3_percentage = int(request.POST.get("term3_percentage", 0) or 0)
        academic_year = request.POST.get("academic_year", str(timezone.now().year)).strip() or str(timezone.now().year)

        fee_structure = FeeStructure.objects.create(
            school=school,
            title=title or "School Fees Structure",
            term=term,
            components=components,
            total_amount=total_amount,
            term1_percentage=term1_percentage,
            term2_percentage=term2_percentage,
            term3_percentage=term3_percentage,
            academic_year=academic_year,
            created_by=request.user,
        )

        # Apply this fee structure to all students in the school by creating/updating
        # their StudentFeeAccount for the specified academic year and term.
        try:
            students = Student.objects.filter(school=school)
            # Determine amount to charge: if a specific term is selected, use split amounts
            split = fee_structure.split_term_amounts()
            for student in students:
                if term and term in split:
                    amt = split[term]
                else:
                    amt = fee_structure.total_amount

                create_student_fee_account(
                    student=student,
                    school=school,
                    academic_year=academic_year,
                    term=term,
                    amount=amt,
                )
        except Exception:
            # Non-fatal: if applying to student accounts fails, still allow structure creation
            pass

        messages.success(request, "Fee structure created successfully.")
        return redirect("fees_dashboard")

    return render(request, "fees/fee_structure_form.html", {
        "school": school,
        "schools": schools,
        "structure": structure,
    })


@login_required
def edit_fee_structure(request, structure_id):
    school = get_school(request.user)
    fee_structure = get_object_or_404(FeeStructure, pk=structure_id)
    schools = School.objects.all() if request.user.is_superuser else []

    if request.method == "POST":
        if request.user.is_superuser:
            school_id = request.POST.get("school")
            if school_id:
                school = get_object_or_404(School, pk=school_id)
        fee_structure.school = school
        fee_structure.title = request.POST.get("title", fee_structure.title).strip()
        fee_structure.term = request.POST.get("term", fee_structure.term).strip()
        fee_structure.components = request.POST.get("components", fee_structure.components).strip()
        fee_structure.total_amount = parse_decimal(request.POST.get("total_amount"))
        fee_structure.term1_percentage = int(request.POST.get("term1_percentage", fee_structure.term1_percentage) or 0)
        fee_structure.term2_percentage = int(request.POST.get("term2_percentage", fee_structure.term2_percentage) or 0)
        fee_structure.term3_percentage = int(request.POST.get("term3_percentage", fee_structure.term3_percentage) or 0)
        fee_structure.academic_year = request.POST.get("academic_year", fee_structure.academic_year).strip() or fee_structure.academic_year
        fee_structure.save()
        messages.success(request, "Fee structure updated successfully.")
        return redirect("fees_dashboard")

    return render(request, "fees/fee_structure_form.html", {
        "school": school,
        "schools": schools,
        "structure": fee_structure,
    })


def _draw_reportlab_watermark(canvas, doc, watermark_text, logo_image=None):
    canvas.saveState()
    watermark_color = colors.Color(0.09, 0.23, 0.49, alpha=0.06)
    canvas.setFillColor(watermark_color)
    canvas.setFont("Helvetica-Bold", 8)
    center_x = doc.leftMargin + doc.width / 2.0
    center_y = doc.bottomMargin + doc.height / 2.0

    for row in range(0, 6):
        for col in range(0, 3):
            x = doc.leftMargin + (col * (doc.width / 2.0)) - 20
            y = doc.bottomMargin + (row * 30)
            canvas.saveState()
            canvas.translate(x, y)
            canvas.rotate(-45)
            canvas.drawString(0, 0, watermark_text)
            canvas.restoreState()

    if logo_image:
        try:
            logo_width = min(doc.width * 0.7, 120 * mm)
            logo_height = min(doc.height * 0.7, 120 * mm)
            x = center_x - (logo_width / 2.0)
            y = center_y - (logo_height / 2.0)
            logo_image.drawWidth = logo_width
            logo_image.drawHeight = logo_height
            logo_image.drawOn(canvas, x, y)
        except Exception:
            pass

    canvas.restoreState()


def _load_reportlab_logo(image_field, width, height):
    if not image_field:
        return None

    def _load_from_url(url):
        try:
            if isinstance(url, str) and url:
                parsed = urlparse(url)
                if parsed.scheme in {"http", "https"} and parsed.netloc:
                    with urlopen(url) as image_file:
                        image_bytes = image_file.read()
                    return RLImage(BytesIO(image_bytes), width=width, height=height)
        except Exception:
            pass
        return None

    logo_url = None
    try:
        logo_url = getattr(image_field, 'url', None)
    except Exception:
        logo_url = None

    if logo_url:
        logo = _load_from_url(logo_url)
        if logo:
            return logo

    logo_path = None
    try:
        logo_path = getattr(image_field, 'path', None)
    except Exception:
        logo_path = None

    if logo_path:
        try:
            return RLImage(logo_path, width=width, height=height)
        except Exception:
            pass

    public_id = None
    try:
        public_id = getattr(image_field, 'public_id', None) or getattr(image_field, 'publicId', None)
    except Exception:
        public_id = None

    if public_id:
        try:
            from cloudinary.utils import cloudinary_url
            cloud_name = None
            cloud_conf = getattr(settings, 'CLOUDINARY_STORAGE', None) or {}
            if isinstance(cloud_conf, dict):
                cloud_name = cloud_conf.get('CLOUD_NAME')
            if cloud_name:
                cloud_url = f"https://res.cloudinary.com/{cloud_name}/image/upload/{public_id}"
                logo = _load_from_url(cloud_url)
                if logo:
                    return logo
        except Exception:
            pass

    if isinstance(image_field, str):
        logo = _load_from_url(image_field)
        if logo:
            return logo

    return None


@login_required
def fee_structure_schedule(request):
    school = get_school(request.user)
    structures = FeeStructure.objects.filter(school=school) if school else FeeStructure.objects.all()
    schedule_rows = []
    summary = {
        "total_term1": Decimal("0"),
        "total_term2": Decimal("0"),
        "total_term3": Decimal("0"),
        "total_expected": Decimal("0"),
    }

    for structure in structures:
        split = structure.split_term_amounts()
        row = {
            "title": structure.title,
            "components": structure.component_lines,
            "term1_amount": split.get("Term 1", Decimal("0")),
            "term2_amount": split.get("Term 2", Decimal("0")),
            "term3_amount": split.get("Term 3", Decimal("0")),
            "amount": structure.total_amount,
        }
        schedule_rows.append(row)
        summary["total_term1"] += row["term1_amount"]
        summary["total_term2"] += row["term2_amount"]
        summary["total_term3"] += row["term3_amount"]
        summary["total_expected"] += row["amount"]

    return render(request, "fees/fee_structure_schedule.html", {
        "school": school,
        "schedule_rows": schedule_rows,
        "summary": summary,
    })


@login_required
def fee_structure_schedule_pdf(request):
    # Generate a PDF of the fee structure schedule with school header and payment notices.
    school = get_school(request.user)
    structures = FeeStructure.objects.filter(school=school) if school else FeeStructure.objects.all()
    mode = request.GET.get('mode', '').lower()
    inline_display = mode == 'print'

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm, topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    normal_style = styles['Normal']
    normal_style.leading = 14
    title_style = styles['Title']
    title_style.spaceAfter = 8

    elements = []

    header_cells = []
    header_text = []
    logo_image = None

    if school and school.logo:
        logo_image = _load_reportlab_logo(school.logo, width=30*mm, height=30*mm)

    header_cells.append(logo_image if logo_image else '')

    if school:
        header_text.append(f"<b>{school.name}</b>")
        if school.address:
            header_text.append(school.address)
        contact_parts = []
        if school.phone:
            contact_parts.append(f"Tel: {school.phone}")
        if school.email:
            contact_parts.append(f"Email: {school.email}")
        if contact_parts:
            header_text.append(' • '.join(contact_parts))
    else:
        header_text.append("Fee Structure Schedule")

    header_paragraph = Paragraph('<br/>'.join(header_text), normal_style)
    header_cells.append(header_paragraph)
    header_table = Table([header_cells], colWidths=[35*mm, doc.width - 35*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW', (0,0), (-1,0), 1.5, colors.HexColor('#163b7d')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Official Fee Structure {year}".format(year=datetime.now().year), title_style))
    elements.append(Spacer(1, 8))

    data = [["Structure", "Term 1", "Term 2", "Term 3", "Total"]]
    summary_term1 = Decimal("0")
    summary_term2 = Decimal("0")
    summary_term3 = Decimal("0")
    summary_total = Decimal("0")

    for s in structures:
        split = s.split_term_amounts()
        t1 = split.get("Term 1", Decimal("0"))
        t2 = split.get("Term 2", Decimal("0"))
        t3 = split.get("Term 3", Decimal("0"))
        description = '<br/>'.join(s.component_lines) if s.component_lines else ''
        title_cell = f"<b>{s.title}</b>"
        if description:
            title_cell += f"<br/><font size=9 color='#444'>{description}</font>"

        data.append([Paragraph(title_cell, normal_style), f"{t1:,.2f}", f"{t2:,.2f}", f"{t3:,.2f}", f"{s.total_amount:,.2f}"])
        summary_term1 += t1
        summary_term2 += t2
        summary_term3 += t3
        summary_total += s.total_amount

    data.append([Paragraph('<b>TOTAL</b>', normal_style), f"{summary_term1:,.2f}", f"{summary_term2:,.2f}", f"{summary_term3:,.2f}", f"{summary_total:,.2f}"])

    table = Table(data, colWidths=[80*mm, 25*mm, 25*mm, 25*mm, 25*mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#f8f8f8')),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 16))

    payment_account_text = "No school payment account has been configured."
    if school and school.bank_name and school.account_number:
        payment_account_text = f"Official Payment Account: {school.bank_name} - {school.account_number}."

    notice_text = (
        "Payment Notice: Please pay only to the official school account shown above. "
        "Payments made to other accounts are not endorsed by the school and may not be recognized. "
        "Ensure you keep proof of payment for verification."
    )

    elements.append(Paragraph(payment_account_text, normal_style))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(notice_text, normal_style))

    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    if inline_display:
        response['Content-Disposition'] = 'inline; filename="fee_structure_schedule.pdf"'
    else:
        response['Content-Disposition'] = 'attachment; filename="fee_structure_schedule.pdf"'
    return response


@login_required
def school_payment_account(request):
    school = get_school(request.user)
    if not school:
        messages.warning(request, "No school payment account is available.")
        return redirect("fees_dashboard")

    if request.method == "POST":
        school.bank_name = request.POST.get("bank_name", school.bank_name)
        school.account_number = request.POST.get("account_number", school.account_number)
        school.save()
        messages.success(request, "School payment account updated.")
        return redirect("school_payment_account")

    return render(request, "fees/school_payment_account.html", {
        "school": school,
    })


@login_required
def verify_receipt(request):
    receipt_number = request.GET.get("receipt_number", "").strip()
    if not receipt_number:
        return JsonResponse({"ok": False, "message": "Receipt number is required."}, status=400)

    invoice = FeeInvoice.objects.filter(receipt_number__iexact=receipt_number).first()
    if not invoice:
        return JsonResponse({"ok": False, "message": "Receipt not found."}, status=404)

    return JsonResponse({
        "ok": True,
        "receipt_number": invoice.receipt_number,
        "invoice_number": invoice.invoice_number,
        "paid": invoice.paid,
        "amount": str(invoice.amount),
        "student": invoice.student.name if invoice.student else invoice.payer_name,
        "school": invoice.school.name,
    })
