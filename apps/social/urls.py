from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FriendViewSet, FriendApplyViewSet, FriendInteractionViewSet

router = DefaultRouter()
router.register(r'friends', FriendViewSet, basename='friend')
router.register(r'applications', FriendApplyViewSet, basename='friend-apply')
router.register(r'interactions', FriendInteractionViewSet, basename='friend-interaction')

urlpatterns = [
    path('', include(router.urls)),
]