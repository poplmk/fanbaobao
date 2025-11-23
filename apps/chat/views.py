from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Max, Count
from django.utils import timezone
from django.core.cache import cache
from apps.utils.response import SuccessResponse, ErrorResponse
from apps.utils.pagination import StandardResultsSetPagination
from apps.utils.decorators import validate_params
from .models import Chat
from .serializers import (
    ChatSerializer, ChatCreateSerializer, ChatListSerializer,
    ConversationPartnerSerializer, ShareContentSerializer, ChatStatsSerializer
)
from .services import ChatService


class ChatViewSet(viewsets.ModelViewSet):
    queryset = Chat.objects.all()
    serializer_class = ChatSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['send_time']
    ordering = ['-send_time']

    def get_serializer_class(self):
        if self.action == 'create':
            return ChatCreateSerializer
        elif self.action == 'list':
            return ChatListSerializer
        return ChatSerializer

    def get_queryset(self):
        # 用户只能看到自己发送或接收的消息
        return Chat.objects.filter(
            Q(sender_openid=self.request.user) | Q(receiver_openid=self.request.user),
            is_deleted=0
        ).select_related('sender_openid', 'receiver_openid')

    def list(self, request, *args, **kwargs):
        """消息列表（按对话分组）"""
        conversation_with = request.query_params.get('with')

        if conversation_with:
            # 获取与特定用户的对话
            return self._get_conversation(request, conversation_with)
        else:
            # 获取所有对话列表
            return self._get_conversations_list(request)

    def _get_conversation(self, request, partner_openid):
        """获取与特定用户的对话"""
        try:
            from apps.user.models import User
            partner = User.objects.get(openid=partner_openid)
        except User.DoesNotExist:
            return ErrorResponse(message='用户不存在')

        # 标记为已读
        Chat.mark_conversation_as_read(request.user, partner)

        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        offset = (page - 1) * page_size

        messages = Chat.get_conversation(request.user, partner, page_size, offset)
        serializer = self.get_serializer(messages, many=True, context={'request': request})

        return SuccessResponse(data={
            'partner': partner_openid,
            'messages': serializer.data,
            'has_more': len(messages) == page_size
        })

    def _get_conversations_list(self, request):
        """获取所有对话列表"""
        conversations = ChatService.get_user_conversations(request.user)
        serializer = ConversationPartnerSerializer(conversations, many=True, context={'request': request})
        return SuccessResponse(data=serializer.data)

    def create(self, request, *args, **kwargs):
        """发送消息"""
        serializer = ChatCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            try:
                message = ChatService.send_message(
                    request.user,
                    serializer.validated_data['receiver_openid'],
                    serializer.validated_data['msg_type'],
                    serializer.validated_data['msg_content']
                )
                result_serializer = ChatSerializer(message, context={'request': request})
                return SuccessResponse(data=result_serializer.data, message='消息发送成功')
            except ValueError as e:
                return ErrorResponse(message=str(e))
        return ErrorResponse(message='发送失败', data=serializer.errors)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """标记消息为已读"""
        message = self.get_object()
        if message.receiver_openid != request.user:
            return ErrorResponse(message='无权操作此消息')

        message.mark_as_read()
        return SuccessResponse(message='消息已标记为已读')

    @action(detail=False, methods=['post'])
    @validate_params(required_params=['partner'])
    def mark_conversation_read(self, request):
        """标记整个对话为已读"""
        partner_openid = request.data.get('partner')
        try:
            from apps.user.models import User
            partner = User.objects.get(openid=partner_openid)
            Chat.mark_conversation_as_read(request.user, partner)
            return SuccessResponse(message='对话已标记为已读')
        except User.DoesNotExist:
            return ErrorResponse(message='用户不存在')

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """未读消息数量"""
        total_unread = Chat.get_unread_count(request.user)
        return SuccessResponse(data={'unread_count': total_unread})

    @action(detail=False, methods=['get'])
    def share_content(self, request):
        """获取可分享的内容"""
        content_type = request.query_params.get('type', 'stall')
        limit = int(request.query_params.get('limit', 10))

        share_content = ChatService.get_share_content(request.user, content_type, limit)
        serializer = ShareContentSerializer(share_content, many=True)
        return SuccessResponse(data=serializer.data)

    @action(detail=False, methods=['get'])
    def search_messages(self, request):
        """搜索消息"""
        query = request.query_params.get('q', '')
        if not query:
            return ErrorResponse(message='请输入搜索关键词')

        messages = ChatService.search_messages(request.user, query)
        page = self.paginate_queryset(messages)

        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(messages, many=True, context={'request': request})
        return SuccessResponse(data=serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """聊天统计"""
        stats = ChatService.get_chat_stats(request.user)
        serializer = ChatStatsSerializer(stats)
        return SuccessResponse(data=serializer.data)

    @action(detail=False, methods=['delete'])
    def clear_conversation(self, request):
        """清空对话（软删除）"""
        partner_openid = request.data.get('partner')
        if not partner_openid:
            return ErrorResponse(message='需要指定对话对象')

        try:
            from apps.user.models import User
            partner = User.objects.get(openid=partner_openid)
            deleted_count = ChatService.clear_conversation(request.user, partner)
            return SuccessResponse(message=f'已删除 {deleted_count} 条消息')
        except User.DoesNotExist:
            return ErrorResponse(message='用户不存在')


class ChatWebSocketViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def ws_token(self, request):
        """获取WebSocket连接令牌"""
        token = ChatService.generate_websocket_token(request.user)
        return SuccessResponse(data={'token': token})

    @action(detail=False, methods=['post'])
    def update_online_status(self, request):
        """更新在线状态"""
        ChatService.update_user_online_status(request.user, True)
        return SuccessResponse(message='在线状态已更新')

    @action(detail=False, methods=['post'])
    def update_offline_status(self, request):
        """更新离线状态"""
        ChatService.update_user_online_status(request.user, False)
        return SuccessResponse(message='离线状态已更新')