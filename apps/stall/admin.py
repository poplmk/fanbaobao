from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Stall


@admin.register(Stall)
class StallAdmin(admin.ModelAdmin):
    list_display = [
        'stall_id', 'stall_name', 'canteen_id', 'praise_rate',
        'popularity_value', 'is_active', 'create_time'
    ]
    list_filter = ['canteen_id', 'is_active', 'create_time']
    search_fields = ['stall_name', 'stall_id', 'canteen_id__canteen_name']
    readonly_fields = ['stall_id', 'create_time', 'update_time']
    list_per_page = 20

    fieldsets = (
        ('基本信息', {
            'fields': ('stall_id', 'canteen_id', 'stall_name', 'stall_image')
        }),
        ('位置信息', {
            'fields': ('window_location', 'business_hours')
        }),
        ('经营信息', {
            'fields': ('payment_method', 'tags', 'is_active')
        }),
        ('统计信息', {
            'fields': ('praise_rate', 'popularity_value')
        }),
        ('时间信息', {
            'fields': ('create_time', 'update_time')
        }),
    )