from decimal import Decimal
import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone


class FeeStructure(models.Model):
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="fee_structures"
    )
    academic_year = models.CharField(max_length=20)
    term = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=200, default="School Fees")
    components = models.TextField(blank=True, default="")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    term1_percentage = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    term2_percentage = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    term3_percentage = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_fee_structures"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["academic_year", "term"]
        unique_together = (
            "school",
            "academic_year",
            "term",
        )

    def __str__(self):
        return f"{self.school.name} - {self.title} ({self.academic_year})"

    @property
    def component_lines(self):
        return [line.strip() for line in self.components.splitlines() if line.strip()]

    def calculate_total(self):
        return sum(
            Decimal(amount.strip().replace(",", ""))
            for _, amount in self.component_items()
        )

    def component_items(self):
        items = []
        for line in self.components.splitlines():
            if ":" in line:
                name, amount = line.split(":", 1)
                try:
                    amount = Decimal(amount.strip().replace(",", ""))
                except Exception:
                    amount = Decimal("0")
                items.append((name.strip(), amount))
        return items

    def save(self, *args, **kwargs):
        if self.components:
            self.total_amount = sum(
                amount for _, amount in self.component_items()
            )
        super().save(*args, **kwargs)

    def split_term_amounts(self):
        percentages = [
            self.term1_percentage,
            self.term2_percentage,
            self.term3_percentage,
        ]
        if sum(percentages) == 0:
            return {}

        return {
            "Term 1": (self.total_amount * Decimal(self.term1_percentage) / Decimal(100)).quantize(Decimal("0.01")),
            "Term 2": (self.total_amount * Decimal(self.term2_percentage) / Decimal(100)).quantize(Decimal("0.01")),
            "Term 3": (self.total_amount * Decimal(self.term3_percentage) / Decimal(100)).quantize(Decimal("0.01")),
        }


class StudentFeeAccount(models.Model):
    STATUS_CHOICES = (
        ("active", "Active"),
        ("closed", "Closed"),
    )

    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="student_fee_accounts"
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="fee_accounts"
    )
    academic_year = models.CharField(max_length=20)
    term = models.CharField(max_length=100, blank=True)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    fees_charged = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    total_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    closing_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    last_payment_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = (
            "student",
            "academic_year",
            "term",
        )

    @property
    def balance(self):
        return self.opening_balance + self.fees_charged - self.total_paid

    def calculate_balance(self):
        paid = FeePayment.objects.filter(account=self).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        self.total_paid = paid
        self.closing_balance = self.opening_balance + self.fees_charged - paid
        return self.closing_balance

    def save(self, *args, **kwargs):
        if self.pk:
            self.calculate_balance()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student.name} - {self.term} ({self.academic_year})"


class FeePayment(models.Model):
    PAYMENT_METHODS = [
        ("cash", "Cash"),
        ("mpesa", "M-Pesa"),
        ("bank", "Bank"),
        ("other", "Other"),
    ]

    account = models.ForeignKey(
        StudentFeeAccount,
        on_delete=models.CASCADE,
        related_name="payments"
    )
    invoice = models.ForeignKey(
        "FeeInvoice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default="cash")
    reference = models.CharField(max_length=100, blank=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_payments"
    )
    date_paid = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_paid"]

    def __str__(self):
        return f"{self.account.student.name} - {self.amount}"

    def save(self, *args, **kwargs):
        if not self.reference:
            while True:
                self.reference = f"PAY-{uuid.uuid4().hex[:12].upper()}"
                if not FeePayment.objects.filter(reference__iexact=self.reference).exists():
                    break
        else:
            existing = FeePayment.objects.filter(reference__iexact=self.reference)
            if self.pk:
                existing = existing.exclude(pk=self.pk)
            if existing.exists():
                raise ValueError("A payment with this reference already exists.")
        super().save(*args, **kwargs)

    @property
    def receipt_number(self):
        if self.invoice:
            return self.invoice.receipt_number
        if self.pk:
            return f"RCP-PAY-{str(self.pk).zfill(6)}"
        return None


class FeeInvoice(models.Model):
    PAYMENT_METHODS = [
        ("cash", "Cash"),
        ("mpesa", "M-Pesa"),
        ("bank", "Bank"),
        ("other", "Other"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("cancelled", "Cancelled"),
    ]

    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="fee_invoices"
    )
    account = models.ForeignKey(
        StudentFeeAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices"
    )
    structure = models.ForeignKey(
        FeeStructure,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices"
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fee_invoices"
    )
    payer_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    due_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default="cash")
    payment_reference = models.CharField(max_length=100, blank=True)
    paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    invoice_number = models.CharField(max_length=50, unique=True, editable=False)
    receipt_number = models.CharField(max_length=50, unique=True, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_fee_invoices"
    )
    served_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_fee_invoices"
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-generated_at"]

    def save(self, *args, **kwargs):
        if self.paid:
            if not self.paid_at:
                self.paid_at = timezone.now()
            if self.status != "paid":
                self.status = "paid"
        if not self.invoice_number:
            self.invoice_number = f"FEE-{uuid.uuid4().hex[:8].upper()}"
        if not self.receipt_number:
            self.receipt_number = f"RCP-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.invoice_number

    @property
    def term(self):
        if self.account and self.account.term:
            return self.account.term
        if self.structure and self.structure.term:
            return self.structure.term
        return ""

    @property
    def student_name(self):
        return self.student.name if self.student else self.payer_name

    def mark_paid(self, payment_method, payment_reference, served_by=None):
        if self.paid:
            return None

        # Prevent duplicate payment records using the same payment reference.
        if payment_reference:
            existing_payment = FeePayment.objects.filter(reference__iexact=payment_reference).first()
            if existing_payment:
                return existing_payment

            existing_invoice = FeeInvoice.objects.filter(
                payment_reference__iexact=payment_reference
            ).exclude(pk=self.pk).first()
            if existing_invoice and existing_invoice.payments.exists():
                return existing_invoice.payments.first()

        self.payment_method = payment_method
        self.payment_reference = payment_reference
        self.paid = True
        self.paid_at = timezone.now()
        self.status = "paid"
        self.served_by = served_by
        self.save()

        payment = FeePayment.objects.create(
            account=self.account,
            invoice=self,
            amount=self.amount,
            payment_method=payment_method,
            reference=payment_reference,
            received_by=served_by
        )

        if self.account:
            self.account.last_payment_date = self.paid_at
            self.account.save()

        return payment

    def is_overdue(self):
        if self.paid or not self.due_date:
            return False
        return self.due_date < timezone.now().date()


class FeeLedger(models.Model):
    TRANSACTION_TYPES = [
        ("debit", "Debit"),
        ("credit", "Credit"),
    ]

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="ledger_entries"
    )
    term = models.CharField(max_length=100, blank=True)
    academic_year = models.CharField(max_length=20, blank=True)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    description = models.TextField(blank=True)
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student.name} - {self.transaction_type} - {self.balance}"
