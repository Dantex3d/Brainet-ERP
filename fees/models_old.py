import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.db.models import Sum

from schools.models import School


# =====================================================
# FEE STRUCTURE
# =====================================================

class FeeStructure(models.Model):

    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="fee_structures"
    )

    title = models.CharField(
        max_length=180,
        default="School Fees Structure"
    )

    term = models.CharField(
        max_length=100,
        blank=True
    )

    components = models.TextField(
        blank=True,
        help_text="Example: Tuition: 15000"
    )

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):
        return f"{self.school.name} - {self.title}"


    def component_items(self):

        items = []

        for line in self.components.splitlines():

            if ":" in line:

                name, amount = line.split(":", 1)

                try:
                    amount = Decimal(
                        amount.strip().replace(",", "")
                    )
                except:
                    amount = Decimal("0")

                items.append(
                    (name.strip(), amount)
                )

        return items


    def calculate_total(self):

        return sum(
            amount for _, amount in self.component_items()
        )


    def save(self, *args, **kwargs):

        if self.components:
            self.total_amount = self.calculate_total()

        super().save(*args, **kwargs)



# =====================================================
# STUDENT FEE ACCOUNT
# =====================================================

class StudentFeeAccount(models.Model):

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="fee_accounts"
    )

    structure = models.ForeignKey(
        FeeStructure,
        on_delete=models.CASCADE,
        related_name="student_accounts"
    )

    expected_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):

        return f"{self.student.name} - {self.structure.title}"


    def amount_paid(self):

        total = self.payments.aggregate(
            total=Sum("amount")
        )["total"]

        return total or Decimal("0")


    def balance(self):

        return (
            self.expected_amount -
            self.amount_paid()
        )



# =====================================================
# FEE PAYMENT
# =====================================================

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


    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )


    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        default="cash"
    )


    reference = models.CharField(
        max_length=100,
        blank=True
    )


    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )


    date_paid = models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):

        return (
            f"{self.account.student.name} "
            f"- {self.amount}"
        )



# =====================================================
# INVOICE / RECEIPT
# =====================================================

class FeeInvoice(models.Model):

    account = models.ForeignKey(
        StudentFeeAccount,
        on_delete=models.CASCADE,
        related_name="invoices"
    )


    payment = models.OneToOneField(
        FeePayment,
        on_delete=models.CASCADE,
        related_name="invoice"
    )


    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        editable=False
    )


    receipt_number = models.CharField(
        max_length=50,
        unique=True,
        editable=False
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )


    def save(self, *args, **kwargs):

        if not self.invoice_number:

            self.invoice_number = (
                "INV-" +
                uuid.uuid4().hex[:8].upper()
            )


        if not self.receipt_number:

            self.receipt_number = (
                "RCP-" +
                uuid.uuid4().hex[:8].upper()
            )


        super().save(*args, **kwargs)


    def __str__(self):

        return self.receipt_number