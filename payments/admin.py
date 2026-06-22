from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'proforma_invoice', 'amount', 'payment_mode',
        'payment_date', 'reference_number', 'created_by', 'created_at',
    )
    list_filter = ('payment_mode', 'payment_date')
    search_fields = (
        'reference_number',
        'proforma_invoice__pi_number',
        'proforma_invoice__customer__name',
    )
    readonly_fields = ('created_at',)
