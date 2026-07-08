from django.test import TestCase
from django.urls import reverse

from brainet.templatetags.text_filters import register
from exams.models import Exam
from schools.models import School, Term, Subject
from students.models import Student
from schools.views import assign_competition_ranks, generate_progress_chart, get_student_term_performance_history
from users.models import CustomUser


class SchoolLogoStorageTests(TestCase):
    def test_get_school_logo_url_filter_is_registered(self):
        self.assertIn("get_school_logo_url", register.filters)

    def test_assign_competition_ranks_skips_tied_positions(self):
        rows = [
            {"score": 100},
            {"score": 100},
            {"score": 90},
            {"score": 80},
            {"score": 80},
        ]

        ranked_rows = assign_competition_ranks(rows, lambda row: row["score"], rank_attr="position")

        self.assertEqual([row["position"] for row in ranked_rows], [1, 1, 3, 4, 4])


class StudentPerformanceHistoryTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="History School",
            address="Test Address",
            phone="0712345678",
            email="school@example.com",
            is_active=True,
            is_verified=True,
        )
        self.user = CustomUser.objects.create_user(
            email="student@example.com",
            password="testpass123",
            role="student",
            school=self.school,
            email_verified=True,
        )
        self.student = Student.objects.create(
            user=self.user,
            school=self.school,
            admission_number="STD0001",
            name="Amina",
            gender="Female",
        )
        self.subject = Subject.objects.create(school=self.school, name="English")
        self.term_2 = Term.objects.create(school=self.school, name="Term 2", start_date="2024-04-01", end_date="2024-06-30")
        self.term_3 = Term.objects.create(school=self.school, name="Term 3", start_date="2024-07-01", end_date="2024-09-30")

    def test_history_starts_from_first_term_with_marks(self):
        from schools.models import StudentMark

        StudentMark.objects.create(student=self.student, subject=self.subject, term=self.term_2, marks=70)
        StudentMark.objects.create(student=self.student, subject=self.subject, term=self.term_3, marks=82)

        history = get_student_term_performance_history(self.student)

        self.assertEqual([entry["term_name"] for entry in history], ["Term 2", "Term 3"])
        self.assertEqual(history[0]["score"], 70.0)
        self.assertEqual(history[1]["score"], 82.0)


class ReportFormTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Report School",
            address="Test Address",
            phone="0712345678",
            email="school@example.com",
            is_active=True,
            is_verified=True,
        )
        self.term = Term.objects.create(
            school=self.school,
            name="Term 1",
            start_date="2024-01-01",
            end_date="2024-03-31",
        )
        self.user = CustomUser.objects.create_user(
            email="principal@example.com",
            password="testpass123",
            role="principal",
            school=self.school,
            email_verified=True,
        )
        self.exam = Exam.objects.create(
            school=self.school,
            term=self.term,
            name="Midterm",
            exam_type="MIDTERM",
            is_active=True,
        )

    def test_generate_progress_chart_returns_png_payload(self):
        payload = generate_progress_chart([70, 82, 91], labels=["Eng", "Math", "Sci"], title="Sample")
        self.assertTrue(payload.startswith("i"))


class ExamWindowTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Test School",
            address="Test Address",
            phone="0712345678",
            email="school@example.com",
            is_active=True,
            is_verified=True,
        )
        self.term = Term.objects.create(
            school=self.school,
            name="Term 1",
            start_date="2024-01-01",
            end_date="2024-03-31",
        )
        self.user = CustomUser.objects.create_user(
            email="principal@example.com",
            password="testpass123",
            role="principal",
            school=self.school,
            email_verified=True,
        )
        self.exam = Exam.objects.create(
            school=self.school,
            term=self.term,
            name="Midterm",
            exam_type="MIDTERM",
            is_active=True,
        )

    def test_close_exam_window_marks_exams_inactive(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("close_exam_window"), follow=True)

        self.assertEqual(response.status_code, 200)
        self.exam.refresh_from_db()
        self.assertFalse(self.exam.is_active)

    def test_enter_marks_shows_warning_when_exam_is_closed(self):
        self.exam.is_active = False
        self.exam.save(update_fields=["is_active"])
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("enter_marks") + f"?class={self.school.id}&exam={self.exam.id}&term={self.term.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "exam is closed")
