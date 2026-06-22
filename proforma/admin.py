from django.contrib import admin

from .models import ProformaInvoice, ProformaLineItem


class ProformaLineItemInline(admin.TabularInline):
    model = ProformaLineItem
    extra = 1
    fields = ('product_name', 'quantity', 'rate', 'amount')


@admin.register(ProformaInvoice)
class ProformaInvoiceAdmin(admin.ModelAdmin):
    list_display = (
        'pi_number', 'date', 'customer', 'currency',
        'total_amount', 'status', 'created_by',
    )
    list_filter = ('status', 'currency', 'date')
    search_fields = ('pi_number', 'customer__name')
    readonly_fields = ('pi_number', 'total_amount', 'created_at', 'updated_at')
    inlines = [ProformaLineItemInline]


@admin.register(ProformaLineItem)
class ProformaLineItemAdmin(admin.ModelAdmin):
    list_display = ('proforma_invoice', 'product_name', 'quantity', 'rate', 'amount')
    search_fields = ('product_name', 'proforma_invoice__pi_number')
