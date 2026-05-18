# billing/admin.py
from django.contrib import admin
from .models import Subscription, BillingLog

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'school',
        'dos',
        'duration',
        'amount',
        'start_date',
        'end_date',
        'days_remaining',
    )
    list_filter = ('duration', 'school')
    search_fields = ('school__name', 'dos__name', 'dos__email')
    ordering = ('-start_date',)

    def days_remaining(self, obj):
        return obj.days_remaining()
    days_remaining.short_description = "Days Remaining"


@admin.register(BillingLog)
class BillingLogAdmin(admin.ModelAdmin):
    list_display = ('subscription', 'status', 'updated_at')
    list_filter = ('status',)
    search_fields = ('subscription__school__name',)
    ordering = ('-updated_at',)
