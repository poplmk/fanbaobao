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
from .models import Dish
from .serializers import (
    DishSerializer, DishCreateSerializer, DishListSerializer,
    DishUpdateSerializer, DishSimpleSerializer, DishSearchSerializer
)
from .services import DishService


class DishViewSet(viewsets.ModelViewSet):
    queryset = Dish.objects.all()
    pagination_class = StandardResultsSetPagination
    permission_classes = [AllowAny]  # 菜品信息允许匿名访问
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['stall_id', 'dish_type', 'is_special', 'is_sold_out']
    search_fields = ['dish_name', 'taste_tag', 'ingredient']
    ordering_fields = ['price', 'create_time', 'is_special']
    ordering = ['-is_special', 'dish_name']

    def get_serializer_class(self):
        if self.action == 'create':
            return DishCreateSerializer
        elif self.action == 'list':
            return DishListSerializer
        elif self.action in ['update', 'partial_update']:
            return DishUpdateSerializer
        elif self.action == 'simple_list':
            return DishSimpleSerializer
        elif self.action == 'search':
            return DishSearchSerializer
        return DishSerializer

    def get_queryset(self):
        queryset = Dish.objects.select_related(
            'stall_id', 'stall_id__canteen_id'
        ).filter(is_sold_out=0)

        # 价格范围筛选
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        # 口味筛选
        taste_filter = self.request.query_params.get('taste', None)
        if taste_filter:
            queryset = queryset.filter(taste_tag__contains=[taste_filter])

        # 食材筛选
        ingredient_filter = self.request.query_params.get('ingredient', None)
        if ingredient_filter:
            queryset = queryset.filter(ingredient__contains=[ingredient_filter])

        return queryset

    def list(self, request, *args, **kwargs):
        """菜品列表"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return SuccessResponse(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """菜品详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, context={'request': request})
        return SuccessResponse(data=serializer.data)

    @action(detail=False, methods=['get'])
    def simple_list(self, request):
        """简化版菜品列表（用于选择器等场景）"""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return SuccessResponse(data=serializer.data)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """菜品搜索"""
        query = request.query_params.get('q', '')
        if not query:
            return ErrorResponse(message='请输入搜索关键词')

        dishes = DishService.search_dishes(query, request.query_params)
        page = self.paginate_queryset(dishes)

        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(dishes, many=True, context={'request': request})
        return SuccessResponse(data=serializer.data)

    @action(detail=False, methods=['get'])
    def specials(self, request):
        """招牌菜品"""
        cache_key = 'special_dishes'
        special_dishes = cache.get(cache_key)

        if special_dishes is None:
            special_dishes = Dish.objects.filter(
                is_special=1,
                is_sold_out=0
            ).select_related(
                'stall_id', 'stall_id__canteen_id'
            ).order_by('-create_time')[:20]

            serializer = DishListSerializer(
                special_dishes, many=True, context={'request': request}
            )
            special_dishes = serializer.data

            # 缓存10分钟
            cache.set(cache_key, special_dishes, 600)

        return SuccessResponse(data=special_dishes)

    @action(detail=False, methods=['get'])
    def by_stall(self, request):
        """按档口获取菜品"""
        stall_id = request.query_params.get('stall_id')
        if not stall_id:
            return ErrorResponse(message='需要提供档口ID')

        dishes = Dish.objects.filter(
            stall_id=stall_id,
            is_sold_out=0
        ).select_related('stall_id').order_by('-is_special', 'dish_name')

        serializer = DishListSerializer(dishes, many=True, context={'request': request})
        return SuccessResponse(data=serializer.data)

    @action(detail=False, methods=['get'])
    def by_canteen(self, request):
        """按食堂获取菜品"""
        canteen_id = request.query_params.get('canteen_id')
        if not canteen_id:
            return ErrorResponse(message='需要提供食堂ID')

        dishes = Dish.objects.filter(
            stall_id__canteen_id=canteen_id,
            is_sold_out=0
        ).select_related('stall_id', 'stall_id__canteen_id').order_by('-is_special', 'dish_name')

        serializer = DishListSerializer(dishes, many=True, context={'request': request})
        return SuccessResponse(data=serializer.data)

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """菜品分类统计"""
        categories = DishService.get_dish_categories()
        return SuccessResponse(data=categories)

    @action(detail=False, methods=['get'])
    def price_ranges(self, request):
        """价格区间统计"""
        price_ranges = DishService.get_price_ranges()
        return SuccessResponse(data=price_ranges)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def toggle_sold_out(self, request, pk=None):
        """切换售罄状态（商家功能）"""
        dish = self.get_object()
        dish.toggle_sold_out()

        message = '已标记为售罄' if dish.is_sold_out else '已恢复供应'
        return SuccessResponse(message=message)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def toggle_special(self, request, pk=None):
        """切换招牌菜状态（商家功能）"""
        dish = self.get_object()
        dish.toggle_special()

        message = '已设为招牌菜' if dish.is_special else '已取消招牌菜'
        return SuccessResponse(message=message)

    @action(detail=True, methods=['get'])
    def recommendations(self, request, pk=None):
        """获取菜品相关推荐内容"""
        dish = self.get_object()
        from apps.recommend.models import Recommend
        from apps.recommend.serializers import RecommendListSerializer

        recommendations = Recommend.objects.filter(
            dish_id=dish.dish_id,
            audit_status='approved',
            is_deleted=0
        ).select_related('openid').order_by('-publish_time')[:10]

        serializer = RecommendListSerializer(
            recommendations, many=True, context={'request': request}
        )
        return SuccessResponse(data=serializer.data)

    @action(detail=True, methods=['get'])
    def similar(self, request, pk=None):
        """相似菜品推荐"""
        dish = self.get_object()
        similar_dishes = DishService.get_similar_dishes(dish)
        serializer = DishListSerializer(
            similar_dishes, many=True, context={'request': request}
        )
        return SuccessResponse(data=serializer.data)