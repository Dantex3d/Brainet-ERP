from django.contrib import admin

from .models import FeeInvoice, FeeStructure


@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ('title', 'school', 'term', 'total_amount', 'created_at')
    search_fields = ('title', 'school__name', 'term')
    list_filter = ('school', 'term')


@admin.register(FeeInvoice)
class FeeInvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'school', 'payer_name', 'amount', 'status', 'payment_method', 'paid', 'paid_at')
    search_fields = ('invoice_number', 'school__name', 'payer_name', 'payment_reference')
    list_filter = ('school', 'status', 'payment_method', 'paid')
