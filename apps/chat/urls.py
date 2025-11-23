from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatViewSet, ChatWebSocketViewSet

router = DefaultRouter()
router.register(r'messages', ChatViewSet, basename='chat')
router.register(r'websocket', ChatWebSocketViewSet, basename='chat-websocket')

urlpatterns = [
    path('', include(router.urls)),
]