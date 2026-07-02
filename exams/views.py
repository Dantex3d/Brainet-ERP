# exams/views.py

from io import BytesIO
from datetime import date
import os
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import qrcode

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image
)
from reportlab.lib.styles import getSampleStyleSheet


def _load_reportlab_image(image_field, width, height):
    if not image_field:
        return None

    image_path = None
    try:
        image_path = image_field.path
    except (AttributeError, NotImplementedError, ValueError, OSError):
        image_path = None

    if image_path:
        try:
            if os.path.exists(image_path):
                return Image(image_path, width=width, height=height)
        except Exception:
            pass

    if hasattr(image_field, "file"):
        try:
            image_field.open()
            return Image(BytesIO(image_field.file.read()), width=width, height=height)
        except Exception:
            pass

    if hasattr(image_field, "url"):
        try:
            with urlopen(image_field.url) as image_file:
                image_bytes = image_file.read()
            return Image(BytesIO(image_bytes), width=width, height=height)
        except (URLError, HTTPError, Exception):
            pass

    return None

from exams.models import Exam
from students.models import Student
from schools.models import Class, Dormitory, Subject, Term
from classes.models import Stream


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
            f'filename="{school_class.name} Class List {date.today().year}.pdf"'
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
            logo = _load_reportlab_image(school.logo, 0.8 * inch, 0.8 * inch)
            if logo:
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
        logo_image = _load_reportlab_image(school.logo, 2.5 * cm, 2.5 * cm)
        if logo_image:
            elements.append(logo_image)

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
from schools.models import  Term
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
    subject = Subject.objects.get(id=data["subject_id"])
    term = Term.objects.get(id=data["term_id"])
    marks = float(data["marks"])

    mark, created = create_or_update_mark(
        student,
        subject,
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
from schools.models import Term
from .services import create_or_update_mark
from subjects.models import ClassSubject

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

@login_required
def exams_class_report(request):
    school = request.user.school
    classes = Class.objects.filter(school=school)
    terms = Term.objects.filter(school=school)
    exams = Exam.objects.filter(school=school)

    class_id = request.GET.get("class_id")
    term_id = request.GET.get("term_id")
    exam_id = request.GET.get("exam_id")
    stream_id = request.GET.get("stream_id")
    combine_requested = request.GET.get("combine") in ["1", "true", "True", "on"]

    error_message = None
    selected_class = None
    selected_term = None
    selected_exam = None
    selected_stream = None
    streams = []

    if class_id:
        selected_class = get_object_or_404(Class, id=class_id, school=school)
        streams = Stream.objects.filter(class_group=selected_class).order_by("name")

        if stream_id:
            selected_stream = get_object_or_404(Stream, id=stream_id, class_group=selected_class)

    if class_id and term_id and exam_id:
        try:
            selected_term = get_object_or_404(Term, id=term_id, school=school)
            selected_exam = get_object_or_404(Exam, id=exam_id, school=school)
        except Exception as e:
            error_message = f"Error: {str(e)}"

    return render(request, "exams/class_report.html", {
        "classes": classes,
        "terms": terms,
        "exams": exams,
        "streams": streams,
        "class_id": class_id,
        "term_id": term_id,
        "exam_id": exam_id,
        "stream_id": stream_id,
        "selected_class": selected_class,
        "selected_term": selected_term,
        "selected_exam": selected_exam,
        "selected_stream": selected_stream,
        "combine_requested": combine_requested,
        "error_message": error_message,
    })

