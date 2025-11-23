from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg
from django.core.cache import cache
from apps.utils.response import SuccessResponse, ErrorResponse
from apps.utils.pagination import StandardResultsSetPagination
from apps.utils.decorators import validate_params
from .models import Stall
from .serializers import (
    StallSerializer, StallCreateSerializer, StallListSerializer,
    StallSimpleSerializer, StallUpdateSerializer
)
from .services import StallService


class StallViewSet(viewsets.ModelViewSet):
    queryset = Stall.objects.all()
    pagination_class = StandardResultsSetPagination
    permission_classes = [AllowAny]  # 档口信息允许匿名访问
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['canteen_id', 'is_active']
    search_fields = ['stall_name', 'tags']
    ordering_fields = ['praise_rate', 'popularity_value', 'create_time']
    ordering = ['-popularity_value']

    def get_serializer_class(self):
        if self.action == 'create':
            return StallCreateSerializer
        elif self.action == 'list':
            return StallListSerializer
        elif self.action in ['update', 'partial_update']:
            return StallUpdateSerializer
        elif self.action == 'simple_list':
            return StallSimpleSerializer
        return StallSerializer

    def get_queryset(self):
        queryset = Stall.objects.select_related('canteen_id').filter(is_active=1)

        # 按标签筛选
        tag_filter = self.request.query_params.get('tag', None)
        if tag_filter:
            queryset = queryset.filter(tags__contains=[tag_filter])

        # 按食堂筛选
        canteen_id = self.request.query_params.get('canteen_id', None)
        if canteen_id:
            queryset = queryset.filter(canteen_id=canteen_id)

        return queryset

    def list(self, request, *args, **kwargs):
        """档口列表"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return SuccessResponse(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """档口详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, context={'request': request})

        # 增加热度值
        instance.popularity_value += 1
        instance.save()

        return SuccessResponse(data=serializer.data)

    @action(detail=False, methods=['get'])
    def simple_list(self, request):
        """简化版档口列表（用于选择器等场景）"""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return SuccessResponse(data=serializer.data)

    @action(detail=False, methods=['get'])
    def popular(self, request):
        """热门档口"""
        cache_key = 'popular_stalls'
        popular_stalls = cache.get(cache_key)

        if popular_stalls is None:
            popular_stalls = Stall.objects.filter(
                is_active=1
            ).select_related('canteen_id').order_by(
                '-popularity_value', '-praise_rate'
            )[:10]

            serializer = StallListSerializer(
                popular_stalls, many=True, context={'request': request}
            )
            popular_stalls = serializer.data

            # 缓存10分钟
            cache.set(cache_key, popular_stalls, 600)

        return SuccessResponse(data=popular_stalls)

    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """附近档口"""
        latitude = request.query_params.get('lat')
        longitude = request.query_params.get('lng')
        radius = request.query_params.get('radius', 2000)

        if not latitude or not longitude:
            return ErrorResponse(message='需要提供经纬度参数')

        try:
            nearby_stalls = StallService.get_nearby_stalls(
                float(latitude), float(longitude), float(radius)
            )
            serializer = StallListSerializer(
                nearby_stalls, many=True, context={'request': request}
            )
            return SuccessResponse(data=serializer.data)
        except ValueError:
            return ErrorResponse(message='经纬度参数格式错误')

    @action(detail=True, methods=['get'])
    def dishes(self, request, pk=None):
        """获取档口的菜品列表"""
        stall = self.get_object()
        from apps.dish.models import Dish
        from apps.dish.serializers import DishListSerializer

        dishes = Dish.objects.filter(
            stall_id=stall.stall_id,
            is_sold_out=0
        ).order_by('-is_special', 'dish_name')

        serializer = DishListSerializer(dishes, many=True, context={'request': request})
        return SuccessResponse(data=serializer.data)

    @action(detail=True, methods=['get'])
    def recommendations(self, request, pk=None):
        """获取档口的推荐内容"""
        stall = self.get_object()
        from apps.recommend.models import Recommend
        from apps.recommend.serializers import RecommendListSerializer

        recommendations = Recommend.objects.filter(
            stall_id=stall.stall_id,
            audit_status='approved',
            is_deleted=0
        ).select_related('openid').order_by('-publish_time')[:20]

        serializer = RecommendListSerializer(
            recommendations, many=True, context={'request': request}
        )
        return SuccessResponse(data=serializer.data)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """档口统计信息"""
        stall = self.get_object()
        stats = StallService.get_stall_stats(stall.stall_id)
        return SuccessResponse(data=stats)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def toggle_collect(self, request, pk=None):
        """收藏/取消收藏档口"""
        stall = self.get_object()
        from apps.recommend.models import Collect

        collected = Collect.objects.filter(
            openid=request.user,
            stall_id=stall.stall_id
        ).exists()

        if collected:
            # 取消收藏
            Collect.objects.filter(
                openid=request.user,
                stall_id=stall.stall_id
            ).delete()
            message = '取消收藏成功'
        else:
            # 添加收藏
            Collect.objects.create(
                openid=request.user,
                stall_id=stall
            )
            message = '收藏成功'

        # 更新收藏数
        stall.update_popularity()

        return SuccessResponse(message=message)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_collected(self, request):
        """我收藏的档口"""
        from apps.recommend.models import Collect
        collected_stalls = Collect.objects.filter(
            openid=request.user
        ).select_related('stall_id', 'stall_id__canteen_id').order_by('-collect_time')

        stalls = [collect.stall_id for collect in collected_stalls]
        serializer = StallListSerializer(stalls, many=True, context={'request': request})
        return SuccessResponse(data=serializer.data)