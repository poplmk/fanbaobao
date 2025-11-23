from django.shortcuts import render

# Create your views here.
from django.db import models
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.core.cache import cache
from apps.utils.response import SuccessResponse, ErrorResponse
from apps.utils.pagination import StandardResultsSetPagination
from apps.utils.decorators import validate_params
from .models import Friend, FriendApply
from .serializers import (
    FriendSerializer, FriendCreateSerializer, FriendUpdateSerializer,
    FriendApplySerializer, FriendApplyCreateSerializer, FriendApplyActionSerializer,
    FriendRecommendSerializer, FriendStatsSerializer
)
from .services import FriendService


class FriendViewSet(viewsets.ModelViewSet):
    queryset = Friend.objects.all()
    serializer_class = FriendSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['friend_openid__nickname', 'remark_name']

    def get_queryset(self):
        return Friend.objects.filter(
            user_openid=self.request.user
        ).select_related('friend_openid').order_by('-last_active_time')

    def list(self, request, *args, **kwargs):
        """好友列表"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return SuccessResponse(data=serializer.data)

    def create(self, request, *args, **kwargs):
        """添加好友（通过用户ID）"""
        serializer = FriendCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            try:
                friend = FriendService.add_friend_directly(
                    request.user,
                    serializer.validated_data['friend_openid'],
                    serializer.validated_data.get('remark_name', '')
                )
                result_serializer = FriendSerializer(friend, context={'request': request})
                return SuccessResponse(data=result_serializer.data, message='好友添加成功')
            except ValueError as e:
                return ErrorResponse(message=str(e))
        return ErrorResponse(message='添加好友失败', data=serializer.errors)

    def destroy(self, request, *args, **kwargs):
        """删除好友"""
        friend = self.get_object()
        FriendService.remove_friend(request.user, friend.friend_openid)
        return SuccessResponse(message='好友删除成功')

    @action(detail=True, methods=['put'])
    def update_remark(self, request, pk=None):
        """更新好友备注"""
        friend = self.get_object()
        serializer = FriendUpdateSerializer(friend, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return SuccessResponse(data=serializer.data, message='备注更新成功')
        return ErrorResponse(message='更新失败', data=serializer.errors)

    @action(detail=False, methods=['get'])
    def online(self, request):
        """在线好友列表"""
        online_friends = FriendService.get_online_friends(request.user)
        serializer = self.get_serializer(online_friends, many=True, context={'request': request})
        return SuccessResponse(data=serializer.data)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """搜索用户（用于添加好友）"""
        query = request.query_params.get('q', '')
        if not query:
            return ErrorResponse(message='请输入搜索关键词')

        users = FriendService.search_users(query, request.user)
        from apps.user.serializers import UserSerializer
        serializer = UserSerializer(users, many=True, context={'request': request})
        return SuccessResponse(data=serializer.data)

    @action(detail=False, methods=['get'])
    def recommendations(self, request):
        """好友推荐"""
        cache_key = f'friend_recommendations:{request.user.openid}'
        recommendations = cache.get(cache_key)

        if recommendations is None:
            recommendations = FriendService.get_friend_recommendations(request.user)
            # 缓存30分钟
            cache.set(cache_key, recommendations, 1800)

        serializer = FriendRecommendSerializer(recommendations, many=True, context={'request': request})
        return SuccessResponse(data=serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """好友统计"""
        stats = FriendService.get_friend_stats(request.user)
        serializer = FriendStatsSerializer(stats)
        return SuccessResponse(data=serializer.data)


class FriendApplyViewSet(viewsets.ModelViewSet):
    queryset = FriendApply.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['apply_status']

    def get_serializer_class(self):
        if self.action == 'create':
            return FriendApplyCreateSerializer
        return FriendApplySerializer

    def get_queryset(self):
        # 用户可以看到自己发送和接收的申请
        return FriendApply.objects.filter(
            Q(applicant_openid=self.request.user) | Q(receiver_openid=self.request.user)
        ).select_related('applicant_openid', 'receiver_openid').order_by('-apply_time')

    def list(self, request, *args, **kwargs):
        """好友申请列表"""
        apply_type = request.query_params.get('type', 'received')  # received or sent

        if apply_type == 'sent':
            queryset = self.get_queryset().filter(applicant_openid=request.user)
        else:
            queryset = self.get_queryset().filter(receiver_openid=request.user)

        queryset = self.filter_queryset(queryset)
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return SuccessResponse(data=serializer.data)

    def create(self, request, *args, **kwargs):
        """发送好友申请"""
        serializer = FriendApplyCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            try:
                apply = FriendService.send_friend_apply(
                    request.user,
                    serializer.validated_data['receiver_openid'],
                    serializer.validated_data.get('apply_msg', '')
                )
                result_serializer = FriendApplySerializer(apply, context={'request': request})
                return SuccessResponse(data=result_serializer.data, message='好友申请发送成功')
            except ValueError as e:
                return ErrorResponse(message=str(e))
        return ErrorResponse(message='发送申请失败', data=serializer.errors)

    @action(detail=True, methods=['post'])
    def handle(self, request, pk=None):
        """处理好友申请"""
        apply = self.get_object()

        # 检查权限
        if apply.receiver_openid != request.user:
            return ErrorResponse(message='无权处理此申请')

        if apply.apply_status != 'pending':
            return ErrorResponse(message='该申请已被处理')

        serializer = FriendApplyActionSerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse(message='参数错误', data=serializer.errors)

        action = serializer.validated_data['action']

        try:
            if action == 'accept':
                apply.accept()
                message = '好友申请已接受'
            else:
                apply.reject()
                message = '好友申请已拒绝'

            result_serializer = FriendApplySerializer(apply, context={'request': request})
            return SuccessResponse(data=result_serializer.data, message=message)

        except ValueError as e:
            return ErrorResponse(message=str(e))

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """取消好友申请（仅申请人可操作）"""
        apply = self.get_object()

        if apply.applicant_openid != request.user:
            return ErrorResponse(message='只能取消自己发送的申请')

        if apply.apply_status != 'pending':
            return ErrorResponse(message='该申请已被处理，无法取消')

        apply.apply_status = 'rejected'
        apply.handle_time = models.DateTimeField(auto_now=True)
        apply.save()

        return SuccessResponse(message='好友申请已取消')

    @action(detail=False, methods=['get'])
    def pending_count(self, request):
        """待处理申请数量"""
        count = FriendApply.objects.filter(
            receiver_openid=request.user,
            apply_status='pending'
        ).count()
        return SuccessResponse(data={'count': count})


class FriendInteractionViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def common_friends(self, request):
        """获取共同好友"""
        target_openid = request.query_params.get('openid')
        if not target_openid:
            return ErrorResponse(message='需要提供用户ID')

        try:
            from apps.user.models import User
            target_user = User.objects.get(openid=target_openid)
            common_friends = FriendService.get_common_friends(request.user, target_user)
            from apps.user.serializers import UserSerializer
            serializer = UserSerializer(common_friends, many=True, context={'request': request})
            return SuccessResponse(data=serializer.data)
        except User.DoesNotExist:
            return ErrorResponse(message='用户不存在')

    @action(detail=False, methods=['get'])
    def friendship_degree(self, request):
        """获取好友亲密度"""
        target_openid = request.query_params.get('openid')
        if not target_openid:
            return ErrorResponse(message='需要提供用户ID')

        try:
            from apps.user.models import User
            target_user = User.objects.get(openid=target_openid)
            degree = FriendService.calculate_friendship_degree(request.user, target_user)
            return SuccessResponse(data={'degree': degree})
        except User.DoesNotExist:
            return ErrorResponse(message='用户不存在')

    @action(detail=False, methods=['post'])
    def update_active_time(self, request):
        """更新用户活跃时间"""
        FriendService.update_user_active_time(request.user)
        return SuccessResponse(message='活跃时间已更新')