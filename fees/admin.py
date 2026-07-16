from django.contrib import admin

from .models import (
    FeeStructure,
    StudentFeeAccount,
    FeePayment,
    FeeLedger,
)


@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = (
        "school",
        "title",
        "academic_year",
        "term",
        "total_amount",
    )
    search_fields = (
        "title",
        "academic_year",
        "term",
    )


@admin.register(StudentFeeAccount)
class StudentFeeAccountAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "academic_year",
        "term",
        "opening_balance",
        "fees_charged",
        "closing_balance",
    )
    search_fields = (
        "student__name",
        "student__admission_number",
    )


@admin.register(FeePayment)
class FeePaymentAdmin(admin.ModelAdmin):
    list_display = (
        "invoice",
        "account",
        "amount",
        "payment_method",
        "date_paid",
    )


@admin.register(FeeLedger)
class FeeLedgerAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "transaction_type",
        "debit",
        "credit",
        "created_at",
    )