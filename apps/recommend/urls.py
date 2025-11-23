from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RecommendViewSet, LikeViewSet, CollectViewSet, CheckinViewSet,
    CommentViewSet, TagViewSet, RecommendStatsViewSet
)

router = DefaultRouter()
router.register(r'recommends', RecommendViewSet, basename='recommend')
router.register(r'likes', LikeViewSet, basename='like')
router.register(r'collects', CollectViewSet, basename='collect')
router.register(r'checkins', CheckinViewSet, basename='checkin')
router.register(r'comments', CommentViewSet, basename='comment')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'stats', RecommendStatsViewSet, basename='recommend-stats')

urlpatterns = [
    path('', include(router.urls)),
]