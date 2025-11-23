from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Friend, FriendApply


@admin.register(Friend)
class FriendAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user_openid', 'friend_openid', 'remark_name',
        'create_time', 'last_active_time'
    ]
    list_filter = ['create_time', 'last_active_time']
    search_fields = [
        'user_openid__nickname', 'friend_openid__nickname', 'remark_name'
    ]
    readonly_fields = ['create_time', 'last_active_time']
    list_per_page = 20

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user_openid', 'friend_openid')


@admin.register(FriendApply)
class FriendApplyAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'applicant_openid', 'receiver_openid', 'apply_status',
        'apply_time', 'handle_time'
    ]
    list_filter = ['apply_status', 'apply_time', 'handle_time']
    search_fields = [
        'applicant_openid__nickname', 'receiver_openid__nickname', 'apply_msg'
    ]
    readonly_fields = ['apply_time', 'handle_time']
    list_per_page = 20

    actions = ['mark_as_accepted', 'mark_as_rejected']

    def mark_as_accepted(self, request, queryset):
        for apply in queryset:
            if apply.apply_status == 'pending':
                apply.accept()

    mark_as_accepted.short_description = "标记选中的申请为已接受"

    def mark_as_rejected(self, request, queryset):
        queryset.filter(apply_status='pending').update(apply_status='rejected')

    mark_as_rejected.short_description = "标记选中的申请为已拒绝"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('applicant_openid', 'receiver_openid')