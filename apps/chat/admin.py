from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Chat


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'sender_openid', 'receiver_openid', 'msg_type',
        'message_summary', 'send_time', 'read_status', 'is_deleted'
    ]
    list_filter = ['msg_type', 'read_status', 'is_deleted', 'send_time']
    search_fields = [
        'sender_openid__nickname', 'receiver_openid__nickname', 'msg_content'
    ]
    readonly_fields = ['send_time']
    list_per_page = 20

    def message_summary(self, obj):
        return obj.get_message_summary()

    message_summary.short_description = '消息摘要'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('sender_openid', 'receiver_openid')