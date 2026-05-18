# exams/views.py

from io import BytesIO

import qrcode

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image
)
from reportlab.lib.styles import getSampleStyleSheet

from students.models import Student
from schools.models import Class, Dormitory


# =========================================================
# GENERATE CLASS LIST PDF
# =========================================================

@login_required
def generate_class_list_pdf(request, class_id):

    school = request.user.school

    school_class = get_object_or_404(
        Class,
        id=class_id,
        school=school
    )

    students = Student.objects.filter(
        current_class=school_class
    ).order_by("name")

    response = HttpResponse(
        content_type="application/pdf"
    )

    response[
        "Content-Disposition"
    ] = (
        f'attachment; '
        f'filename="{school_class.name}_class_list.pdf"'
    )

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20,
    )

    elements = []

    styles = getSampleStyleSheet()

    # =====================================================
    # SCHOOL LOGO
    # =====================================================

    if school.logo:
        try:
            logo = Image(
                school.logo.path,
                width=2.5 * cm,
                height=2.5 * cm
            )

            elements.append(logo)

        except Exception:
            pass

    # =====================================================
    # SCHOOL HEADER
    # =====================================================

    title = Paragraph(
        f"""
        <font size='18'>
        <b>{school.name.upper()}</b>
        </font>
        """,
        styles["Title"]
    )

    elements.append(title)

    elements.append(
        Spacer(1, 0.2 * cm)
    )

    subtitle = Paragraph(
        f"""
        <font size='12'>
        <u>OFFICIAL CLASS LIST - {school_class.name}</u>
        </font>
        """,
        styles["Heading2"]
    )

    elements.append(subtitle)

    elements.append(
        Spacer(1, 0.5 * cm)
    )

    # =====================================================
    # TABLE DATA
    # =====================================================

    data = [[
        "No",
        "Admission No",
        "Student Name",
        "Gender",
        "Dormitory"
    ]]

    for index, student in enumerate(students, start=1):

        dorm_name = (
            student.dormitory.name
            if student.dormitory
            else "-"
        )

        data.append([
            str(index),
            student.admission_number,
            student.name,
            student.gender,
            dorm_name
        ])

    # =====================================================
    # TABLE
    # =====================================================

    table = Table(
        data,
        colWidths=[
            1.5 * cm,
            4 * cm,
            7 * cm,
            2.5 * cm,
            4 * cm
        ]
    )

    table.setStyle(TableStyle([

        # HEADER
        (
            "BACKGROUND",
            (0, 0),
            (-1, 0),
            colors.darkblue
        ),

        (
            "TEXTCOLOR",
            (0, 0),
            (-1, 0),
            colors.white
        ),

        (
            "FONTNAME",
            (0, 0),
            (-1, 0),
            "Helvetica-Bold"
        ),

        (
            "FONTSIZE",
            (0, 0),
            (-1, -1),
            10
        ),

        (
            "BOTTOMPADDING",
            (0, 0),
            (-1, 0),
            10
        ),

        # BODY
        (
            "BACKGROUND",
            (0, 1),
            (-1, -1),
            colors.beige
        ),

        (
            "GRID",
            (0, 0),
            (-1, -1),
            1,
            colors.black
        ),

        (
            "ALIGN",
            (0, 0),
            (-1, -1),
            "CENTER"
        ),

    ]))

    elements.append(table)

    elements.append(
        Spacer(1, 0.5 * cm)
    )

    # =====================================================
    # TOTAL STUDENTS
    # =====================================================

    total = Paragraph(
        f"""
        <b>Total Students:</b> {students.count()}
        """,
        styles["Normal"]
    )

    elements.append(total)

    elements.append(
        Spacer(1, 0.5 * cm)
    )

    # =====================================================
    # QR CODE
    # =====================================================

    qr_data = (
        f"Class List Verification | "
        f"{school.name} | "
        f"{school_class.name}"
    )

    qr = qrcode.make(qr_data)

    qr_buffer = BytesIO()

    qr.save(qr_buffer, format="PNG")

    qr_buffer.seek(0)

    qr_image = Image(
        qr_buffer,
        width=3 * cm,
        height=3 * cm
    )

    elements.append(qr_image)

    elements.append(
        Spacer(1, 0.5 * cm)
    )

    # =====================================================
    # FOOTER
    # =====================================================

    footer = Paragraph(
        """
        <font size='9'>
        Generated by Brainet Analytics School ERP
        </font>
        """,
        styles["Normal"]
    )

    elements.append(footer)

    # =====================================================
    # BUILD PDF
    # =====================================================

    doc.build(elements)

    return response


# =========================================================
# GENERATE DORMITORY LIST PDF
# =========================================================

@login_required
def generate_dorm_list_pdf(request, dorm_id):

    school = request.user.school

    dormitory = get_object_or_404(
        Dormitory,
        id=dorm_id,
        school=school
    )

    students = Student.objects.filter(
        dormitory=dormitory
    ).order_by("name")

    response = HttpResponse(
        content_type="application/pdf"
    )

    response[
        "Content-Disposition"
    ] = (
        f'attachment; '
        f'filename="{dormitory.name}_dormitory_list.pdf"'
    )

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20,
    )

    elements = []

    styles = getSampleStyleSheet()

    # =====================================================
    # SCHOOL LOGO
    # =====================================================

    if school.logo:
        try:
            logo = Image(
                school.logo.path,
                width=2.5 * cm,
                height=2.5 * cm
            )

            elements.append(logo)

        except Exception:
            pass

    # =====================================================
    # HEADER
    # =====================================================

    title = Paragraph(
        f"""
        <font size='18'>
        <b>{school.name.upper()}</b>
        </font>
        """,
        styles["Title"]
    )

    elements.append(title)

    elements.append(
        Spacer(1, 0.2 * cm)
    )

    subtitle = Paragraph(
        f"""
        <font size='12'>
        <u>DORMITORY LIST - {dormitory.name}</u>
        </font>
        """,
        styles["Heading2"]
    )

    elements.append(subtitle)

    elements.append(
        Spacer(1, 0.5 * cm)
    )

    # =====================================================
    # TABLE DATA
    # =====================================================

    data = [[
        "No",
        "Admission No",
        "Student Name",
        "Class",
        "Gender"
    ]]

    for index, student in enumerate(students, start=1):

        class_name = (
            student.current_class.name
            if student.current_class
            else "-"
        )

        data.append([
            str(index),
            student.admission_number,
            student.name,
            class_name,
            student.gender
        ])

    # =====================================================
    # TABLE
    # =====================================================

    table = Table(
        data,
        colWidths=[
            1.5 * cm,
            4 * cm,
            7 * cm,
            4 * cm,
            2.5 * cm
        ]
    )

    table.setStyle(TableStyle([

        (
            "BACKGROUND",
            (0, 0),
            (-1, 0),
            colors.darkgreen
        ),

        (
            "TEXTCOLOR",
            (0, 0),
            (-1, 0),
            colors.white
        ),

        (
            "FONTNAME",
            (0, 0),
            (-1, 0),
            "Helvetica-Bold"
        ),

        (
            "GRID",
            (0, 0),
            (-1, -1),
            1,
            colors.black
        ),

        (
            "BACKGROUND",
            (0, 1),
            (-1, -1),
            colors.whitesmoke
        ),

        (
            "ALIGN",
            (0, 0),
            (-1, -1),
            "CENTER"
        ),

    ]))

    elements.append(table)

    elements.append(
        Spacer(1, 0.5 * cm)
    )

    # =====================================================
    # TOTAL
    # =====================================================

    total = Paragraph(
        f"""
        <b>Total Students:</b> {students.count()}
        """,
        styles["Normal"]
    )

    elements.append(total)

    elements.append(
        Spacer(1, 0.5 * cm)
    )

    # =====================================================
    # QR CODE
    # =====================================================

    qr_data = (
        f"Dormitory Verification | "
        f"{school.name} | "
        f"{dormitory.name}"
    )

    qr = qrcode.make(qr_data)

    qr_buffer = BytesIO()

    qr.save(qr_buffer, format="PNG")

    qr_buffer.seek(0)

    qr_image = Image(
        qr_buffer,
        width=3 * cm,
        height=3 * cm
    )

    elements.append(qr_image)

    elements.append(
        Spacer(1, 0.5 * cm)
    )

    # =====================================================
    # FOOTER
    # =====================================================

    footer = Paragraph(
        """
        <font size='9'>
        Generated by Brainet Analytics School ERP
        </font>
        """,
        styles["Normal"]
    )

    elements.append(footer)

    # =====================================================
    # BUILD PDF
    # =====================================================

    doc.build(elements)

    return response
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from students.models import Student
from schools.models import ClassSubject, Term
from .services import create_or_update_mark


@csrf_exempt
def enter_mark(request):
    """
    Teacher submits marks here
    """

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    data = json.loads(request.body)

    student = Student.objects.get(id=data["student_id"])
    class_subject = ClassSubject.objects.get(id=data["class_subject_id"])
    term = Term.objects.get(id=data["term_id"])
    marks = float(data["marks"])

    mark, created = create_or_update_mark(
        student,
        class_subject,
        term,
        marks
    )

    return JsonResponse({
        "success": True,
        "created": created,
        "student": student.name,
        "marks": str(mark.marks),
        "grade": mark.grade,
        "points": str(mark.points)
    })
# exams/views.py
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from students.models import Student
from schools.models import ClassSubject, Term
from .services import create_or_update_mark


@csrf_exempt
def bulk_enter_marks(request):
    """
    Receives list of marks like Excel sheet
    """

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    data = json.loads(request.body)

    term = Term.objects.get(id=data["term_id"])
    class_subject = ClassSubject.objects.get(id=data["class_subject_id"])

    results = []

    for row in data["marks"]:
        student = Student.objects.get(id=row["student_id"])
        mark_value = float(row["marks"])

        mark, created = create_or_update_mark(
            student,
            class_subject,
            term,
            mark_value
        )

        results.append({
            "student": student.name,
            "marks": str(mark.marks),
            "grade": mark.grade,
            "created": created
        })

    return JsonResponse({
        "success": True,
        "results": results
    })    
    