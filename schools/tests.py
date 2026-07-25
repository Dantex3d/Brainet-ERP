from django.core import mail
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from brainet.templatetags.text_filters import register
from exams.models import Exam
from schools.models import School, Term, Subject, StudentMark, ContactMessage, DOSMessage, Notification, DemoRequest
from students.models import Student
from schools.views import assign_competition_ranks, generate_progress_chart, get_student_term_performance_history, get_combined_mark_for_reporting
from schools.promotion_service import PromotionService
from users.models import CustomUser


class SchoolModelImportTests(SimpleTestCase):
    def test_school_models_import_without_cloudinary_dependency(self):
        from schools import models

        self.assertTrue(hasattr(models, "School"))
        self.assertTrue(hasattr(models, "DirectorOfStudies"))


class PromotionStageTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Promotion School",
            address="Test Address",
            phone="0712345678",
            email="promotion@example.com",
            is_active=True,
            is_verified=True,
        )

    def test_primary_to_junior_is_allowed_within_same_school(self):
        primary_class = self.school.classes_app_classes.create(name="Grade 6", level=6)
        junior_class = self.school.classes_app_classes.create(name="Grade 7", level=7)

        next_class, next_stream = PromotionService.get_next_class(primary_class)

        self.assertEqual(next_class, junior_class)
        self.assertIsNone(next_stream)

    def test_junior_to_senior_exits_the_school_flow(self):
        junior_class = self.school.classes_app_classes.create(name="Grade 9", level=9)

        next_class, next_stream = PromotionService.get_next_class(junior_class)

        self.assertIsNone(next_class)
        self.assertIsNone(next_stream)


class DemoRequestWorkflowTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Demo School",
            address="Test Address",
            phone="0712345679",
            email="demoschool-demo@example.com",
            is_active=True,
            is_verified=True,
        )
        self.superuser = CustomUser.objects.create_user(
            email="demo-super@example.com",
            password="testpass123",
            role="superuser",
            school=self.school,
            email_verified=True,
        )
        self.superuser.is_superuser = True
        self.superuser.save(update_fields=["is_superuser"])

    def test_public_demo_request_is_saved_for_superuser_review(self):
        response = self.client.post(
            reverse("request_demo"),
            {
                "full_name": "Jane Demo",
                "email": "jane-demo@example.com",
                "phone": "0712345678",
                "intended_school": "Bright Grove School",
                "position_rank": "Principal",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(DemoRequest.objects.filter(email="jane-demo@example.com", status="pending").exists())

    def test_superuser_can_approve_demo_request(self):
        demo_request = DemoRequest.objects.create(
            full_name="Jane Demo",
            email="jane-demo@example.com",
            phone="0712345678",
            intended_school="Bright Grove School",
            position_rank="Principal",
        )
        self.client.force_login(self.superuser)

        response = self.client.post(reverse("approve_demo_request", args=[demo_request.id]), follow=True)

        self.assertEqual(response.status_code, 200)
        demo_request.refresh_from_db()
        self.assertEqual(demo_request.status, "approved")
        self.assertEqual(demo_request.reviewed_by, self.superuser)


class ContactMessageFlowTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Support School",
            address="Test Address",
            phone="0712345680",
            email="supportschool-demo@example.com",
            is_active=True,
            is_verified=True,
        )
        self.superuser = CustomUser.objects.create_user(
            email="super@example.com",
            password="testpass123",
            role="superuser",
            school=self.school,
            email_verified=True,
        )
        self.superuser.is_superuser = True
        self.superuser.save(update_fields=["is_superuser"])

    def test_contact_submit_stores_message_for_superuser(self):
        response = self.client.post(
            reverse("contact_submit"),
            {
                "name": "Jane Doe",
                "email": "jane@example.com",
                "phone": "0712345678",
                "message": "Need help with setup",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(ContactMessage.objects.filter(email="jane@example.com").exists())

    def test_contact_submit_stores_browser_and_ip(self):
        response = self.client.post(
            reverse("contact_submit"),
            {
                "name": "Jane Doe",
                "email": "jane@example.com",
                "phone": "0712345678",
                "message": "Need help with setup",
            },
            HTTP_USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            REMOTE_ADDR="203.0.113.10",
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        message = ContactMessage.objects.get(email="jane@example.com")
        self.assertIn("Mozilla/5.0", message.browser_used)
        self.assertEqual(message.ip_address, "203.0.113.10")

    def test_superuser_can_reply_to_contact_message(self):
        message = ContactMessage.objects.create(
            name="Jane Doe",
            email="jane@example.com",
            phone="0712345678",
            message="Need help with setup",
        )
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse("superuser_contact_reply", args=[message.id]),
            {"reply": "We will help shortly."},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        message.refresh_from_db()
        self.assertTrue(message.handled)
        self.assertEqual(message.reply, "We will help shortly.")


class SuperuserSchoolEditTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Edit School",
            address="Test Address",
            phone="0712345678",
            email="edit@example.com",
            bank_name="ABC Bank",
            account_number="1234567890",
            is_active=True,
            is_verified=True,
        )
        self.superuser = CustomUser.objects.create_user(
            email="superedit@example.com",
            password="testpass123",
            role="superuser",
            school=self.school,
            email_verified=True,
        )
        self.superuser.is_superuser = True
        self.superuser.save(update_fields=["is_superuser"])

    def test_superuser_school_edit_form_excludes_bank_fields(self):
        self.client.force_login(self.superuser)

        response = self.client.get(reverse("edit_school", args=[self.school.id]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Bank Name")
        self.assertNotContains(response, "Account Number")


class SuperuserNotificationClearTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Notify School",
            address="Test Address",
            phone="0712345678",
            email="notify@example.com",
            is_active=True,
            is_verified=True,
        )
        self.superuser = CustomUser.objects.create_user(
            email="notify-super@example.com",
            password="testpass123",
            role="superuser",
            school=self.school,
            email_verified=True,
        )
        self.superuser.is_superuser = True
        self.superuser.save(update_fields=["is_superuser"])
        self.notification = Notification.objects.create(
            school=self.school,
            sender=self.superuser,
            recipient=self.superuser,
            title="System update",
            message="A new update is available",
        )
        self.message = DOSMessage.objects.create(
            school=self.school,
            sender=self.superuser,
            receiver=self.superuser,
            subject="Pending review",
            message="A message needs attention",
            status="pending",
        )

    def test_reset_notification_count_clears_superuser_notifications(self):
        self.client.force_login(self.superuser)

        response = self.client.post(reverse("reset_notification_count"), follow=True)

        self.assertRedirects(response, reverse("superuser_dashboard"))
        self.assertEqual(Notification.objects.filter(recipient=self.superuser).count(), 0)
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, "cleared")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SchoolRegistrationFlowTests(TestCase):
    def test_public_school_registration_creates_school_admin_and_sends_login_email(self):
        response = self.client.post(
            reverse("register_school"),
            {
                "name": "Bright Future School",
                "address": "123 Main Street",
                "phone": "0712345678",
                "email": "bright@example.com",
                "admin_name": "Alice Maina",
                "admin_email": "admin@example.com",
                "admin_phone": "0723456789",
                "admin_password": "StrongPass123",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        school = School.objects.get(email="bright@example.com")
        self.assertTrue(school.principals.exists())

        principal = school.principals.get()
        self.assertEqual(principal.name, "Alice Maina")
        self.assertEqual(principal.email, "admin@example.com")
        self.assertIsNotNone(principal.user)
        self.assertTrue(principal.user.email_verified)

        sent_messages = [message.subject for message in mail.outbox]
        self.assertIn("Verify your school registration on Brainet", sent_messages)
        self.assertIn("Your Brainet school admin account", sent_messages)

        login_email = next(message for message in mail.outbox if message.to == ["admin@example.com"])
        self.assertIn("Temporary password", login_email.body)
        self.assertIn("/login/", login_email.body)


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


class CombinedExamReportTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Combo School",
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
        self.subject = Subject.objects.create(school=self.school, name="English")
        self.student = Student.objects.create(
            school=self.school,
            admission_number="STD0002",
            name="Benedict",
            gender="Male",
        )
        self.opening_exam = Exam.objects.create(
            school=self.school,
            term=self.term,
            name="Opening Exam",
            exam_type="OPENING",
            is_active=True,
        )
        self.midterm_exam = Exam.objects.create(
            school=self.school,
            term=self.term,
            name="Midterm Exam",
            exam_type="MIDTERM",
            is_active=True,
        )

    def test_combined_mark_uses_average_of_term_exams(self):
        from schools.models import StudentMark

        StudentMark.objects.create(student=self.student, subject=self.subject, term=self.term, exam=self.opening_exam, marks=70)
        StudentMark.objects.create(student=self.student, subject=self.subject, term=self.term, exam=self.midterm_exam, marks=90)

        combined_mark = get_combined_mark_for_reporting(self.student, self.subject, self.term, combine_requested=True)

        self.assertEqual(combined_mark, 80.0)


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


class MarksEntryDisplayTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Marks School",
            address="Test Address",
            phone="0712345678",
            email="marks@example.com",
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
            email="principal2@example.com",
            password="testpass123",
            role="principal",
            school=self.school,
            email_verified=True,
        )
        self.class_obj = self.school.classes_app_classes.create(name="Grade 7", level=7)
        self.subject = Subject.objects.create(school=self.school, name="English")
        self.student = Student.objects.create(
            school=self.school,
            admission_number="STD0003",
            name="Alice",
            gender="Female",
            current_class=self.class_obj,
        )
        StudentMark.objects.create(
            student=self.student,
            subject=self.subject,
            term=self.term,
            marks=78,
            grade="B",
            points=3,
        )

    def test_enter_marks_displays_existing_marks_without_exam_filter(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("enter_marks") + f"?class={self.class_obj.id}&subject={self.subject.id}&term={self.term.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="78"')
        self.assertContains(response, "Current: 78")

    def test_enter_marks_has_bulk_entry_toggle(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("enter_marks") + f"?class={self.class_obj.id}&subject={self.subject.id}&term={self.term.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="entry_mode" value="bulk"')

    def test_bulk_entry_page_renders_without_crashing(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("enter_marks") + f"?class={self.class_obj.id}&term={self.term.id}&entry_mode=bulk"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Student Name")
        self.assertContains(response, "Admission No")
        self.assertContains(response, self.subject.name)
        self.assertContains(response, 'name="mark_')


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
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

    def test_dashboard_uses_session_exam_window_state_when_present(self):
        self.exam.is_active = False
        self.exam.save(update_fields=["is_active"])
        self.client.force_login(self.user)
        self.client.session[f"exam_window_state_{self.school.id}"] = "open"
        self.client.session.save()

        response = self.client.get(reverse("dos_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["exam_window_open"])
        self.assertContains(response, "Open")

    def test_enter_marks_shows_warning_when_exam_is_closed(self):
        self.exam.is_active = False
        self.exam.save(update_fields=["is_active"])
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("enter_marks") + f"?class={self.school.id}&exam={self.exam.id}&term={self.term.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "exam is closed")
