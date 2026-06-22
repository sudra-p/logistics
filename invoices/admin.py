from django.contrib import admin

from .models import (
    CommercialInvoice,
    CommercialInvoiceLineItem,
    PackingList,
    PackingListLineItem,
)


class CommercialInvoiceLineItemInline(admin.TabularInline):
    model = CommercialInvoiceLineItem
    extra = 1
    fields = (
        'product_name', 'quantity', 'rate', 'amount',
        'net_weight', 'gross_weight', 'hs_code', 'num_packages',
    )


@admin.register(CommercialInvoice)
class CommercialInvoiceAdmin(admin.ModelAdmin):
    list_display = (
        'invoice_number', 'booking', 'revision', 'status',
        'created_by', 'created_at',
    )
    list_filter = ('status', 'revision')
    search_fields = ('invoice_number', 'booking__job_number')
    readonly_fields = ('invoice_number', 'created_at', 'updated_at')
    inlines = [CommercialInvoiceLineItemInline]


@admin.register(CommercialInvoiceLineItem)
class CommercialInvoiceLineItemAdmin(admin.ModelAdmin):
    list_display = (
        'commercial_invoice', 'product_name', 'quantity', 'rate', 'amount',
    )
    search_fields = ('product_name', 'commercial_invoice__invoice_number')


class PackingListLineItemInline(admin.TabularInline):
    model = PackingListLineItem
    extra = 1
    fields = (
        'product_name', 'quantity', 'num_packages',
        'net_weight', 'gross_weight', 'package_type',
    )


@admin.register(PackingList)
class PackingListAdmin(admin.ModelAdmin):
    list_display = (
        'packing_list_number', 'booking', 'revision', 'status',
        'created_by', 'created_at',
    )
    list_filter = ('status', 'revision')
    search_fields = ('packing_list_number', 'booking__job_number')
    readonly_fields = ('packing_list_number', 'created_at', 'updated_at')
    inlines = [PackingListLineItemInline]


@admin.register(PackingListLineItem)
class PackingListLineItemAdmin(admin.ModelAdmin):
    list_display = (
        'packing_list', 'product_name', 'quantity',
        'num_packages', 'net_weight', 'gross_weight',
    )
    search_fields = ('product_name', 'packing_list__packing_list_number')
