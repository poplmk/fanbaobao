from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Recommend, Like, Collect, Checkin, Comment, Tag


@admin.register(Recommend)
class RecommendAdmin(admin.ModelAdmin):
    list_display = [
        'recommend_id', 'openid', 'stall_id', 'audit_status',
        'like_count', 'comment_count', 'publish_time', 'is_deleted'
    ]
    list_filter = ['audit_status', 'is_deleted', 'publish_time']
    search_fields = ['content', 'openid__nickname', 'stall_id__stall_name']
    readonly_fields = ['recommend_id', 'publish_time', 'audit_time']
    list_per_page = 20

    actions = ['approve_recommendations', 'reject_recommendations']

    def approve_recommendations(self, request, queryset):
        queryset.update(audit_status='approved')

    approve_recommendations.short_description = "审核通过选中的推荐"

    def reject_recommendations(self, request, queryset):
        queryset.update(audit_status='rejected')

    reject_recommendations.short_description = "审核不通过选中的推荐"


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ['id', 'openid', 'recommend_id', 'like_time']
    list_filter = ['like_time']
    search_fields = ['openid__nickname', 'recommend_id__content']


@admin.register(Collect)
class CollectAdmin(admin.ModelAdmin):
    list_display = ['id', 'openid', 'stall_id', 'collect_time']
    list_filter = ['collect_time']
    search_fields = ['openid__nickname', 'stall_id__stall_name']


@admin.register(Checkin)
class CheckinAdmin(admin.ModelAdmin):
    list_display = ['checkin_id', 'openid', 'stall_id', 'rating', 'checkin_time']
    list_filter = ['rating', 'checkin_time']
    search_fields = ['openid__nickname', 'stall_id__stall_name']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['comment_id', 'openid', 'recommend_id', 'create_time', 'is_deleted']
    list_filter = ['is_deleted', 'create_time']
    search_fields = ['openid__nickname', 'content']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['tag_id', 'tag_name', 'tag_type', 'create_time']
    list_filter = ['tag_type']
    search_fields = ['tag_name']