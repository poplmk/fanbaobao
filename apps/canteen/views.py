from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from apps.utils.response import SuccessResponse, ErrorResponse
from apps.utils.pagination import StandardResultsSetPagination
from .models import Canteen
from .serializers import CanteenSerializer, CanteenCreateSerializer, CanteenListSerializer
from .services import CanteenService


class CanteenViewSet(viewsets.ModelViewSet):
    queryset = Canteen.objects.all()
    pagination_class = StandardResultsSetPagination
    permission_classes = [AllowAny]  # 食堂信息允许匿名访问
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active']

    def get_serializer_class(self):
        if self.action == 'create':
            return CanteenCreateSerializer
        elif self.action in ['list', 'nearby']:
            return CanteenListSerializer
        return CanteenSerializer

    def get_queryset(self):
        queryset = Canteen.objects.filter(is_active=1)

        # 搜索功能
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(canteen_name__icontains=search) |
                Q(address__icontains=search)
            )

        return queryset.order_by('-stall_count')

    def list(self, request, *args, **kwargs):
        """食堂列表"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return SuccessResponse(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """食堂详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return SuccessResponse(data=serializer.data)

    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """附近食堂"""
        latitude = request.query_params.get('lat')
        longitude = request.query_params.get('lng')
        radius = request.query_params.get('radius', 2000)  # 默认2公里

        if not latitude or not longitude:
            return ErrorResponse(message='需要提供经纬度参数')

        try:
            canteens = CanteenService.get_nearby_canteens(
                float(latitude),
                float(longitude),
                float(radius)
            )
            serializer = self.get_serializer(canteens, many=True)
            return SuccessResponse(data=serializer.data)
        except ValueError:
            return ErrorResponse(message='经纬度参数格式错误')

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """食堂统计信息"""
        canteen = self.get_object()
        stats = CanteenService.get_canteen_stats(canteen.canteen_id)
        return SuccessResponse(data=stats)