from django.contrib import admin

from inventory.models import StockItem


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'available_stock', 'reserved_stock', 'shipped_stock', 'unit', 'updated_at']
    search_fields = ['product_name']
    list_filter = ['unit']
    readonly_fields = ['updated_at']
