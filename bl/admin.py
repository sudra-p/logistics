from django.contrib import admin

from .models import BillOfLading


@admin.register(BillOfLading)
class BillOfLadingAdmin(admin.ModelAdmin):
    list_display = (
        'bl_number', 'booking', 'bl_type', 'status',
        'vessel_name', 'voyage_number', 'created_by', 'created_at',
    )
    list_filter = ('status', 'bl_type')
    search_fields = (
        'bl_number', 'booking__job_number',
        'vessel_name', 'container_number',
    )
    readonly_fields = ('created_at', 'updated_at')
