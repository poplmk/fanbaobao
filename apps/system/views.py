from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.core.cache import cache
from apps.utils.response import SuccessResponse, ErrorResponse
from apps.utils.pagination import StandardResultsSetPagination
from apps.utils.decorators import validate_params
from .models import Notice, FeedbackType, Feedback, Policy
from .serializers import (
    NoticeSerializer, NoticeCreateSerializer,
    FeedbackTypeSerializer, FeedbackSerializer, FeedbackCreateSerializer, FeedbackUpdateSerializer,
    PolicySerializer, PolicyCreateSerializer, SystemStatsSerializer
)
from .services import SystemService


class NoticeViewSet(viewsets.ModelViewSet):
    queryset = Notice.objects.all()
    serializer_class = NoticeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['notice_type', 'read_status']
    ordering_fields = ['send_time']
    ordering = ['-send_time']

    def get_serializer_class(self):
        if self.action == 'create':
            return NoticeCreateSerializer
        return NoticeSerializer

    def get_queryset(self):
        return Notice.objects.filter(openid=self.request.user).select_related('openid')

    def list(self, request, *args, **kwargs):
        """通知列表"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return SuccessResponse(data=serializer.data)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """标记通知为已读"""
        notice = self.get_object()
        if notice.openid != request.user:
            return ErrorResponse(message='无权操作此通知')

        notice.mark_as_read()
        return SuccessResponse(message='通知已标记为已读')

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """标记所有通知为已读"""
        Notice.objects.filter(
            openid=request.user,
            read_status=0
        ).update(read_status=1)

        return SuccessResponse(message='所有通知已标记为已读')

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """未读通知数量"""
        count = Notice.objects.filter(
            openid=request.user,
            read_status=0
        ).count()
        return SuccessResponse(data={'unread_count': count})

    @action(detail=False, methods=['get'])
    def types(self, request):
        """通知类型统计"""
        stats = Notice.objects.filter(
            openid=request.user
        ).values('notice_type').annotate(
            total=Count('notice_id'),
            unread=Count('notice_id', filter=Q(read_status=0))
        )
        return SuccessResponse(data=list(stats))


class FeedbackTypeViewSet(viewsets.ModelViewSet):
    queryset = FeedbackType.objects.all()
    serializer_class = FeedbackTypeSerializer
    permission_classes = [AllowAny]  # 反馈类型允许匿名访问
    pagination_class = None  # 不需要分页

    def list(self, request, *args, **kwargs):
        """反馈类型列表"""
        cache_key = 'feedback_types'
        feedback_types = cache.get(cache_key)

        if feedback_types is None:
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            feedback_types = serializer.data
            # 缓存1天
            cache.set(cache_key, feedback_types, 86400)

        return SuccessResponse(data=feedback_types)


class FeedbackViewSet(viewsets.ModelViewSet):
    queryset = Feedback.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['feedback_type', 'handle_status']
    ordering_fields = ['submit_time']
    ordering = ['-submit_time']

    def get_serializer_class(self):
        if self.action == 'create':
            return FeedbackCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return FeedbackUpdateSerializer
        return FeedbackSerializer

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Feedback.objects.all().select_related('openid', 'feedback_type')
        return Feedback.objects.filter(openid=self.request.user).select_related('openid', 'feedback_type')

    def list(self, request, *args, **kwargs):
        """反馈列表"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return SuccessResponse(data=serializer.data)

    def create(self, request, *args, **kwargs):
        """提交反馈"""
        serializer = FeedbackCreateSerializer(data=request.data)
        if serializer.is_valid():
            feedback = serializer.save(openid=request.user)
            result_serializer = FeedbackSerializer(feedback, context={'request': request})
            return SuccessResponse(data=result_serializer.data, message='反馈提交成功')
        return ErrorResponse(message='提交失败', data=serializer.errors)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def admin_reply(self, request, pk=None):
        """获取管理员回复（用户查看）"""
        feedback = self.get_object()
        if feedback.openid != request.user and not request.user.is_superuser:
            return ErrorResponse(message='无权查看此反馈')

        if feedback.handle_status == 'pending':
            return SuccessResponse(data={'reply': None}, message='反馈待处理')

        return SuccessResponse(data={
            'reply': feedback.reply,
            'handle_status': feedback.handle_status,
            'handle_time': feedback.handle_time
        })

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_stats(self, request):
        """我的反馈统计"""
        stats = Feedback.objects.filter(
            openid=request.user
        ).aggregate(
            total=Count('feedback_id'),
            pending=Count('feedback_id', filter=Q(handle_status='pending')),
            processing=Count('feedback_id', filter=Q(handle_status='processing')),
            resolved=Count('feedback_id', filter=Q(handle_status='resolved'))
        )
        return SuccessResponse(data=stats)


class PolicyViewSet(viewsets.ModelViewSet):
    queryset = Policy.objects.all()
    permission_classes = [AllowAny]  # 政策内容允许匿名访问
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.action == 'create':
            return PolicyCreateSerializer
        return PolicySerializer

    def list(self, request, *args, **kwargs):
        """政策列表"""
        cache_key = 'policy_list'
        policies = cache.get(cache_key)

        if policies is None:
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            policies = serializer.data
            # 缓存1小时
            cache.set(cache_key, policies, 3600)

        return SuccessResponse(data=policies)

    def retrieve(self, request, *args, **kwargs):
        """政策详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return SuccessResponse(data=serializer.data)

    @action(detail=False, methods=['get'])
    def latest(self, request):
        """最新政策"""
        cache_key = 'latest_policy'
        latest_policy = cache.get(cache_key)

        if latest_policy is None:
            latest_policy = Policy.objects.order_by('-update_time').first()
            if latest_policy:
                serializer = self.get_serializer(latest_policy)
                latest_policy = serializer.data
                # 缓存1天
                cache.set(cache_key, latest_policy, 86400)

        return SuccessResponse(data=latest_policy)


class SystemStatsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def overview(self, request):
        """系统概览统计（管理员）"""
        if not request.user.is_superuser:
            return ErrorResponse(message='权限不足')

        cache_key = 'system_stats_overview'
        stats = cache.get(cache_key)

        if stats is None:
            stats = SystemService.get_system_overview()
            # 缓存5分钟
            cache.set(cache_key, stats, 300)

        serializer = SystemStatsSerializer(stats)
        return SuccessResponse(data=serializer.data)

    @action(detail=False, methods=['get'])
    def user_stats(self, request):
        """用户个人统计"""
        stats = SystemService.get_user_stats(request.user)
        return SuccessResponse(data=stats)


class NotificationViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    @validate_params(required_params=['type', 'content'])
    def send(self, request):
        """发送通知（管理员功能）"""
        if not request.user.is_superuser:
            return ErrorResponse(message='权限不足')

        notice_type = request.data.get('type')
        content = request.data.get('content')
        jump_url = request.data.get('jump_url')
        target_users = request.data.get('target_users')  # 为空则发送给所有用户

        try:
            sent_count = SystemService.send_notification_to_users(
                notice_type, content, jump_url, target_users
            )
            return SuccessResponse(message=f'通知发送成功，共发送给 {sent_count} 个用户')
        except ValueError as e:
            return ErrorResponse(message=str(e))

    @action(detail=False, methods=['get'])
    def templates(self, request):
        """通知模板"""
        templates = SystemService.get_notification_templates()
        return SuccessResponse(data=templates)