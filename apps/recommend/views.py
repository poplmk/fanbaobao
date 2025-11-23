from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.core.cache import cache
from apps.utils.response import SuccessResponse, ErrorResponse
from apps.utils.pagination import StandardResultsSetPagination
from apps.utils.decorators import validate_params
from .models import Recommend, Like, Collect, Checkin, Comment, Tag
from .serializers import (
    RecommendSerializer, RecommendCreateSerializer, RecommendListSerializer,
    LikeSerializer, CollectSerializer, CheckinSerializer, CheckinCreateSerializer,
    CommentSerializer, CommentCreateSerializer, TagSerializer, RecommendStatsSerializer
)
from .services import RecommendService


class RecommendViewSet(viewsets.ModelViewSet):
    queryset = Recommend.objects.all()
    pagination_class = StandardResultsSetPagination
    permission_classes = [AllowAny]  # 推荐内容允许匿名访问
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['stall_id', 'dish_id', 'audit_status']
    search_fields = ['content', 'tags']
    ordering_fields = ['like_count', 'collect_count', 'comment_count', 'publish_time']
    ordering = ['-publish_time']

    def get_serializer_class(self):
        if self.action == 'create':
            return RecommendCreateSerializer
        elif self.action == 'list':
            return RecommendListSerializer
        return RecommendSerializer

    def get_queryset(self):
        queryset = Recommend.objects.select_related(
            'openid', 'stall_id', 'stall_id__canteen_id', 'dish_id'
        ).filter(
            audit_status='approved',
            is_deleted=0
        )

        # 用户筛选
        user_filter = self.request.query_params.get('user', None)
        if user_filter:
            queryset = queryset.filter(openid=user_filter)

        # 标签筛选
        tag_filter = self.request.query_params.get('tag', None)
        if tag_filter:
            queryset = queryset.filter(tags__contains=[tag_filter])

        return queryset

    def list(self, request, *args, **kwargs):
        """推荐内容列表"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return SuccessResponse(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """推荐内容详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, context={'request': request})
        return SuccessResponse(data=serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def create_recommend(self, request):
        """创建推荐内容"""
        serializer = RecommendCreateSerializer(data=request.data)
        if serializer.is_valid():
            recommend = serializer.save(openid=request.user)
            result_serializer = RecommendSerializer(recommend, context={'request': request})
            return SuccessResponse(data=result_serializer.data, message='推荐内容发布成功，等待审核')
        return ErrorResponse(message='发布失败', data=serializer.errors)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def toggle_like(self, request, pk=None):
        """点赞/取消点赞"""
        recommend = self.get_object()
        liked = Like.objects.filter(
            openid=request.user,
            recommend_id=recommend
        ).exists()

        if liked:
            # 取消点赞
            Like.objects.filter(
                openid=request.user,
                recommend_id=recommend
            ).delete()
            recommend.decrement_like_count()
            message = '取消点赞成功'
        else:
            # 添加点赞
            Like.objects.create(
                openid=request.user,
                recommend_id=recommend
            )
            recommend.increment_like_count()
            message = '点赞成功'

        return SuccessResponse(message=message)

    @action(detail=True, methods=['get'])
    def likes(self, request, pk=None):
        """获取点赞用户列表"""
        recommend = self.get_object()
        likes = Like.objects.filter(
            recommend_id=recommend
        ).select_related('openid').order_by('-like_time')

        serializer = LikeSerializer(likes, many=True, context={'request': request})
        return SuccessResponse(data=serializer.data)

    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        """获取评论列表"""
        recommend = self.get_object()
        comments = Comment.objects.filter(
            recommend_id=recommend,
            is_deleted=0
        ).select_related('openid', 'reply_to').order_by('create_time')

        serializer = CommentSerializer(comments, many=True, context={'request': request})
        return SuccessResponse(data=serializer.data)

    @action(detail=False, methods=['get'])
    def hot(self, request):
        """热门推荐"""
        cache_key = 'hot_recommends'
        hot_recommends = cache.get(cache_key)

        if hot_recommends is None:
            hot_recommends = Recommend.objects.filter(
                audit_status='approved',
                is_deleted=0
            ).select_related(
                'openid', 'stall_id', 'stall_id__canteen_id'
            ).order_by(
                '-like_count', '-comment_count', '-publish_time'
            )[:20]

            serializer = RecommendListSerializer(
                hot_recommends, many=True, context={'request': request}
            )
            hot_recommends = serializer.data

            # 缓存10分钟
            cache.set(cache_key, hot_recommends, 600)

        return SuccessResponse(data=hot_recommends)

    @action(detail=False, methods=['get'])
    def following(self, request):
        """关注用户的推荐（需要登录）"""
        if not request.user.is_authenticated:
            return ErrorResponse(message='请先登录')

        from apps.social.models import Friend
        # 获取关注的好友列表
        friends = Friend.objects.filter(user_openid=request.user).values_list('friend_openid', flat=True)

        recommends = Recommend.objects.filter(
            openid__in=friends,
            audit_status='approved',
            is_deleted=0
        ).select_related(
            'openid', 'stall_id', 'stall_id__canteen_id'
        ).order_by('-publish_time')

        page = self.paginate_queryset(recommends)
        if page is not None:
            serializer = RecommendListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = RecommendListSerializer(recommends, many=True, context={'request': request})
        return SuccessResponse(data=serializer.data)


class LikeViewSet(viewsets.ModelViewSet):
    queryset = Like.objects.all()
    serializer_class = LikeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Like.objects.filter(openid=self.request.user).select_related('recommend_id')

    def list(self, request, *args, **kwargs):
        """我点赞的内容"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return SuccessResponse(data=serializer.data)


class CollectViewSet(viewsets.ModelViewSet):
    queryset = Collect.objects.all()
    serializer_class = CollectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Collect.objects.filter(openid=self.request.user).select_related('stall_id')

    def list(self, request, *args, **kwargs):
        """我收藏的档口"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return SuccessResponse(data=serializer.data)


class CheckinViewSet(viewsets.ModelViewSet):
    queryset = Checkin.objects.all()
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return CheckinCreateSerializer
        return CheckinSerializer

    def get_queryset(self):
        return Checkin.objects.filter(openid=self.request.user).select_related('stall_id')

    def list(self, request, *args, **kwargs):
        """我的打卡记录"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return SuccessResponse(data=serializer.data)

    def create(self, request, *args, **kwargs):
        """创建打卡记录"""
        serializer = CheckinCreateSerializer(data=request.data)
        if serializer.is_valid():
            # 检查今天是否已经打过卡
            today = timezone.now().date()
            today_checkin = Checkin.objects.filter(
                openid=request.user,
                stall_id=serializer.validated_data['stall_id'],
                checkin_time__date=today
            ).exists()

            if today_checkin:
                return ErrorResponse(message='今天已经在该档口打过卡了')

            checkin = serializer.save(openid=request.user)
            result_serializer = CheckinSerializer(checkin, context={'request': request})
            return SuccessResponse(data=result_serializer.data, message='打卡成功')
        return ErrorResponse(message='打卡失败', data=serializer.errors)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """打卡统计"""
        stats = Checkin.objects.filter(
            openid=request.user
        ).aggregate(
            total_checkins=Count('checkin_id'),
            avg_rating=Avg('rating'),
            today_checkins=Count('checkin_id', filter=Q(checkin_time__date=timezone.now().date()))
        )
        return SuccessResponse(data=stats)


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return CommentCreateSerializer
        return CommentSerializer

    def get_queryset(self):
        return Comment.objects.filter(openid=self.request.user, is_deleted=0).select_related('recommend_id')

    def list(self, request, *args, **kwargs):
        """我的评论"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return SuccessResponse(data=serializer.data)

    def create(self, request, *args, **kwargs):
        """创建评论"""
        serializer = CommentCreateSerializer(data=request.data)
        if serializer.is_valid():
            comment = serializer.save(openid=request.user)
            result_serializer = CommentSerializer(comment, context={'request': request})
            return SuccessResponse(data=result_serializer.data, message='评论成功')
        return ErrorResponse(message='评论失败', data=serializer.errors)

    @action(detail=True, methods=['post'])
    def delete_comment(self, request, pk=None):
        """删除评论（软删除）"""
        comment = self.get_object()
        if comment.openid != request.user:
            return ErrorResponse(message='无权删除此评论')

        comment.is_deleted = 1
        comment.save()
        comment.recommend_id.decrement_comment_count()

        return SuccessResponse(message='评论删除成功')


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def list(self, request, *args, **kwargs):
        """标签列表"""
        tag_type = request.query_params.get('type', None)
        if tag_type:
            queryset = Tag.objects.filter(tag_type=tag_type)
        else:
            queryset = self.filter_queryset(self.get_queryset())

        serializer = self.get_serializer(queryset, many=True)
        return SuccessResponse(data=serializer.data)

    @action(detail=False, methods=['get'])
    def popular(self, request):
        """热门标签"""
        cache_key = 'popular_tags'
        popular_tags = cache.get(cache_key)

        if popular_tags is None:
            # 统计推荐内容中标签的使用频率
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT tag, COUNT(*) as count 
                    FROM recommend, JSON_TABLE(tags, '$[*]' COLUMNS(tag VARCHAR(50) PATH '$')) AS jt 
                    WHERE audit_status = 'approved' AND is_deleted = 0 
                    GROUP BY tag 
                    ORDER BY count DESC 
                    LIMIT 20
                """)
                popular_tags = [{'tag_name': row[0], 'count': row[1]} for row in cursor.fetchall()]

            # 缓存30分钟
            cache.set(cache_key, popular_tags, 1800)

        return SuccessResponse(data=popular_tags)


class RecommendStatsViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'])
    def overview(self, request):
        """推荐系统概览统计"""
        cache_key = 'recommend_stats_overview'
        stats = cache.get(cache_key)

        if stats is None:
            stats = RecommendService.get_system_stats()
            # 缓存5分钟
            cache.set(cache_key, stats, 300)

        serializer = RecommendStatsSerializer(stats)
        return SuccessResponse(data=serializer.data)