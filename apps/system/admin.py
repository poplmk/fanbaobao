from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Notice, FeedbackType, Feedback, Policy


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = [
        'notice_id', 'openid', 'notice_type', 'notice_content_summary',
        'read_status', 'send_time'
    ]
    list_filter = ['notice_type', 'read_status', 'send_time']
    search_fields = ['openid__nickname', 'notice_content']
    readonly_fields = ['notice_id', 'send_time']
    list_per_page = 20

    def notice_content_summary(self, obj):
        return obj.notice_content[:30] + '...' if len(obj.notice_content) > 30 else obj.notice_content

    notice_content_summary.short_description = '通知内容'


@admin.register(FeedbackType)
class FeedbackTypeAdmin(admin.ModelAdmin):
    list_display = ['feedback_type_id', 'type_name']
    search_fields = ['type_name']


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = [
        'feedback_id', 'openid', 'feedback_type', 'content_summary',
        'handle_status', 'submit_time', 'handle_time'
    ]
    list_filter = ['feedback_type', 'handle_status', 'submit_time']
    search_fields = ['openid__nickname', 'content']
    readonly_fields = ['feedback_id', 'submit_time']
    list_per_page = 20

    actions = ['mark_as_processing', 'mark_as_resolved', 'mark_as_rejected']

    def content_summary(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content

    content_summary.short_description = '反馈内容'

    def mark_as_processing(self, request, queryset):
        queryset.update(handle_status='processing')

    mark_as_processing.short_description = "标记选中的反馈为处理中"

    def mark_as_resolved(self, request, queryset):
        queryset.update(handle_status='resolved')

    mark_as_resolved.short_description = "标记选中的反馈为已解决"

    def mark_as_rejected(self, request, queryset):
        queryset.update(handle_status='rejected')

    mark_as_rejected.short_description = "标记选中的反馈为不予处理"


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ['policy_id', 'policy_name', 'update_time']
    search_fields = ['policy_name']
    readonly_fields = ['policy_id', 'update_time']