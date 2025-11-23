from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NoticeViewSet, FeedbackTypeViewSet, FeedbackViewSet,
    PolicyViewSet, SystemStatsViewSet, NotificationViewSet
)

router = DefaultRouter()
router.register(r'notices', NoticeViewSet, basename='notice')
router.register(r'feedback-types', FeedbackTypeViewSet, basename='feedback-type')
router.register(r'feedbacks', FeedbackViewSet, basename='feedback')
router.register(r'policies', PolicyViewSet, basename='policy')
router.register(r'stats', SystemStatsViewSet, basename='system-stats')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
]