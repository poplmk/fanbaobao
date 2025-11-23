from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, UserPreferViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'preferences', UserPreferViewSet, basename='user-prefer')

urlpatterns = [
    path('', include(router.urls)),
]