from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CanteenViewSet

router = DefaultRouter()
router.register(r'canteens', CanteenViewSet, basename='canteen')

urlpatterns = [
    path('', include(router.urls)),
]