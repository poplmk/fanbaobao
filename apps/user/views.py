from django.shortcuts import render

# Create your views here.
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from apps.utils.response import SuccessResponse, ErrorResponse
from apps.utils.decorators import validate_params
from .models import User, UserPrefer
from .serializers import (
    UserSerializer, UserCreateSerializer, UserPreferSerializer,
    UserPreferUpdateSerializer, UserLoginSerializer
)
from .services import UserService


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']

    def get_queryset(self):
        if self.request.user.is_superuser:
            return User.objects.all()
        return User.objects.filter(openid=self.request.user.openid)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    @validate_params(required_params=['code'])
    def login(self, request):
        """微信登录"""
        serializer = UserLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse(message='参数验证失败', data=serializer.errors)

        try:
            result = UserService.wechat_login(
                code=serializer.validated_data['code'],
                nickname=serializer.validated_data.get('nickname'),
                avatar_url=serializer.validated_data.get('avatar_url')
            )
            return SuccessResponse(data=result, message='登录成功')
        except Exception as e:
            return ErrorResponse(message=str(e))

    @action(detail=False, methods=['get'])
    def profile(self, request):
        """获取当前用户信息"""
        serializer = self.get_serializer(request.user)
        return SuccessResponse(data=serializer.data)

    @action(detail=False, methods=['put'])
    def update_profile(self, request):
        """更新用户信息"""
        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return SuccessResponse(data=serializer.data, message='更新成功')
        return ErrorResponse(message='更新失败', data=serializer.errors)


class UserPreferViewSet(viewsets.ModelViewSet):
    queryset = UserPrefer.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return UserPreferUpdateSerializer
        return UserPreferSerializer

    def get_queryset(self):
        return UserPrefer.objects.filter(openid=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        """获取用户偏好"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return SuccessResponse(data=serializer.data)

    def create(self, request, *args, **kwargs):
        """创建用户偏好"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # 确保每个用户只有一个偏好设置
            prefer, created = UserPrefer.objects.get_or_create(
                openid=request.user,
                defaults=serializer.validated_data
            )
            if not created:
                # 如果已存在，则更新
                for attr, value in serializer.validated_data.items():
                    setattr(prefer, attr, value)
                prefer.save()

            result_serializer = UserPreferSerializer(prefer)
            return SuccessResponse(
                data=result_serializer.data,
                message='偏好设置保存成功'
            )
        return ErrorResponse(message='参数验证失败', data=serializer.errors)

    def update(self, request, *args, **kwargs):
        """更新用户偏好"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            result_serializer = UserPreferSerializer(instance)
            return SuccessResponse(data=result_serializer.data, message='更新成功')
        return ErrorResponse(message='更新失败', data=serializer.errors)

    @action(detail=False, methods=['get'])
    def my_prefer(self, request):
        """获取当前用户的偏好设置"""
        try:
            prefer = UserPrefer.objects.get(openid=request.user)
            serializer = self.get_serializer(prefer)
            return SuccessResponse(data=serializer.data)
        except UserPrefer.DoesNotExist:
            return SuccessResponse(data=None, message='暂无偏好设置')