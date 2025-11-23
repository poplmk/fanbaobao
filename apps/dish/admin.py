from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Dish


@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display = [
        'dish_id', 'dish_name', 'stall_id', 'price', 'dish_type',
        'is_special', 'is_sold_out', 'create_time'
    ]
    list_filter = ['stall_id', 'dish_type', 'is_special', 'is_sold_out', 'create_time']
    search_fields = ['dish_name', 'dish_id', 'stall_id__stall_name']
    readonly_fields = ['dish_id', 'create_time', 'update_time']
    list_per_page = 20

    fieldsets = (
        ('基本信息', {
            'fields': ('dish_id', 'stall_id', 'dish_name', 'dish_image')
        }),
        ('菜品详情', {
            'fields': ('price', 'dish_type', 'taste_tag', 'ingredient')
        }),
        ('状态管理', {
            'fields': ('is_special', 'is_sold_out')
        }),
        ('时间信息', {
            'fields': ('create_time', 'update_time')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('stall_id')