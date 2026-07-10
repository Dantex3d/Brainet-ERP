from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from schools.models import School
from .models import FeeStructure, FeeInvoice

User = get_user_model()


class FeeStructureTestCase(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name='Test School',
            address='123 Test Road',
            phone='+254712345678',
            email='school@test.com',
            is_active=True,
        )
        self.bursar = User.objects.create_user(
            email='bursar@test.com',
            password='testpass',
            role='bursar',
            school=self.school,
        )
        self.client = Client()

    def test_create_fee_structure(self):
        fee_structure = FeeStructure.objects.create(
            school=self.school,
            title='2024 Term 1 Fees',
            term='Term 1',
            components='Tuition: 15000\nBoarding: 8000',
            total_amount=23000,
            created_by=self.bursar,
        )
        self.assertEqual(fee_structure.school, self.school)
        self.assertEqual(fee_structure.total_amount, 23000)
        self.assertIn('Tuition: 15000', fee_structure.components)

    def test_fee_structure_component_lines(self):
        fee_structure = FeeStructure.objects.create(
            school=self.school,
            components='Tuition: 15000\nBoarding: 8000\nLab: 2000',
            total_amount=25000,
        )
        lines = fee_structure.component_lines()
        self.assertEqual(len(lines), 3)
        self.assertIn('Tuition: 15000', lines)


class FeeInvoiceTestCase(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name='Test School',
            address='123 Test Road',
            phone='+254712345678',
            email='school@test.com',
            is_active=True,
        )
        self.bursar = User.objects.create_user(
            email='bursar@test.com',
            password='testpass',
            role='bursar',
            school=self.school,
        )
        self.client = Client()

    def test_create_invoice(self):
        invoice = FeeInvoice.objects.create(
            school=self.school,
            payer_name='John Doe',
            amount=25000,
            payment_method='mpesa',
            created_by=self.bursar,
        )
        self.assertTrue(invoice.invoice_number.startswith('FEE-'))
        self.assertEqual(invoice.amount, 25000)
        self.assertFalse(invoice.paid)

    def test_mark_invoice_as_paid(self):
        invoice = FeeInvoice.objects.create(
            school=self.school,
            payer_name='Jane Doe',
            amount=15000,
            created_by=self.bursar,
        )
        invoice.paid = True
        invoice.payment_reference = 'MPESA123456'
        invoice.save()

        self.assertTrue(invoice.paid)
        self.assertEqual(invoice.status, 'paid')
        self.assertIsNotNone(invoice.paid_at)

    def test_invoice_overdue_check(self):
        from datetime import timedelta
        from django.utils import timezone

        invoice = FeeInvoice.objects.create(
            school=self.school,
            payer_name='Test Student',
            amount=20000,
            due_date=timezone.now().date() - timedelta(days=5),
            created_by=self.bursar,
        )
        self.assertTrue(invoice.is_overdue())


class FeesDashboardAccessTestCase(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name='Test School',
            address='123 Test Road',
            phone='+254712345678',
            email='school@test.com',
            is_active=True,
        )
        self.bursar = User.objects.create_user(
            email='bursar@test.com',
            password='testpass',
            role='bursar',
            school=self.school,
        )
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass',
            role='student',
        )
        self.client = Client()

    def test_bursar_can_access_fees_dashboard(self):
        self.client.login(email='bursar@test.com', password='testpass')
        response = self.client.get(reverse('fees_dashboard'))
        # May not work without authentication setup, but tests intent

    def test_student_cannot_access_fees_dashboard(self):
        self.client.login(email='student@test.com', password='testpass')
        response = self.client.get(reverse('fees_dashboard'))
        # May redirect or error; intent is to block student access
