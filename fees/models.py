import uuid
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from schools.models import School


class FeeStructure(models.Model):
    APPROVAL_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='fee_structures')
    title = models.CharField(max_length=180, default='School Fees Structure')
    term = models.CharField(max_length=100, blank=True)
    components = models.TextField(blank=True, help_text='Enter one component per line such as Tuition: 15000')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    approval_status = models.CharField(max_length=20, choices=APPROVAL_CHOICES, default='pending')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_fee_structures')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_fee_structures')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.school.name} - {self.title} ({self.term or "General"})'

    def component_lines(self):
        return [line.strip() for line in self.components.splitlines() if line.strip()]
    
    def is_approved(self):
        return self.approval_status == 'approved'


class FeeInvoice(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('bank', 'Bank Transfer'),
        ('mpesa', 'M-Pesa'),
        ('cash', 'Cash'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    
    APPROVAL_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='fee_invoices')
    structure = models.ForeignKey(FeeStructure, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    payer_name = models.CharField(max_length=200, blank=True)
    invoice_number = models.CharField(max_length=40, unique=True, editable=False)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approval_status = models.CharField(max_length=20, choices=APPROVAL_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='mpesa')
    payment_reference = models.CharField(max_length=120, blank=True)
    paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_fee_invoices')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    receipt_number = models.CharField(max_length=50, unique=True, editable=False, blank=True, null=True)
    receipt_verification_code = models.CharField(max_length=32, unique=True, editable=False, blank=True, null=True)
    served_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_fee_invoices')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_fee_invoices')
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-generated_at']

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = f'FEE-{uuid.uuid4().hex[:8].upper()}'
        if not self.receipt_number and self.paid:
            self.receipt_number = self._generate_receipt_number()
            self.receipt_verification_code = self._generate_verification_code()
        if self.paid and not self.paid_at:
            self.paid_at = timezone.now()
        if self.paid:
            self.status = 'paid'
        return super().save(*args, **kwargs)

    def _generate_receipt_number(self):
        """Generate Safaricom-style receipt number: RCP-DDMMYY-ABC123-56789"""
        import random
        import string
        date_part = timezone.now().strftime('%d%m%y')
        alpha_part = ''.join(random.choices(string.ascii_uppercase, k=3))
        numeric_part1 = ''.join(random.choices(string.digits, k=3))
        numeric_part2 = ''.join(random.choices(string.digits, k=5))
        return f'RCP-{date_part}-{alpha_part}{numeric_part1}-{numeric_part2}'

    def _generate_verification_code(self):
        """Generate a unique system verification code for fraud prevention"""
        import hashlib
        unique_str = f'{self.invoice_number}{self.school.id}{self.amount}{timezone.now().isoformat()}{uuid.uuid4()}'
        return hashlib.sha256(unique_str.encode()).hexdigest()[:32].upper()

    def verify_receipt(self, receipt_number, verification_code=None):
        """Verify receipt authenticity"""
        if self.receipt_number != receipt_number:
            return False
        if verification_code and self.receipt_verification_code != verification_code:
            return False
        return True
    
    def is_approved(self):
        return self.approval_status == 'approved'


    def __str__(self):
        return f'{self.invoice_number} — {self.school.name} — {self.amount}'

    def receipt_title(self):
        return f'Receipt: {self.invoice_number}'

    def is_overdue(self):
        if self.due_date and not self.paid:
            return self.due_date < timezone.now().date()
        return False
