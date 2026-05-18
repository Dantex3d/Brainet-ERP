# reports/models.py
from django.db import models
from students.models import Student
from exams.models import Exam
from schools.models import School, Term

class Report(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    generated_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to='reports/')
    qr_code = models.ImageField(upload_to='reports/qrcodes/', null=True, blank=True)

    def __str__(self):
        return f"Report for {self.student.full_name} - {self.exam.name}"
