from rest_framework import serializers
from .models import Recommend, Like, Collect, Checkin, Comment, Tag
from apps.user.serializers import UserSerializer
from apps.stall.serializers import StallSimpleSerializer
from apps.dish.serializers import DishSimpleSerializer


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['tag_id', 'tag_name', 'tag_type', 'create_time']
        read_only_fields = ['tag_id', 'create_time']


class RecommendSerializer(serializers.ModelSerializer):
    user_info = UserSerializer(source='openid', read_only=True)
    stall_info = StallSimpleSerializer(source='stall_id', read_only=True)
    dish_info = DishSimpleSerializer(source='dish_id', read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_collected = serializers.SerializerMethodField()

    class Meta:
        model = Recommend
        fields = [
            'recommend_id', 'openid', 'user_info', 'stall_id', 'stall_info',
            'dish_id', 'dish_info', 'images', 'content', 'tags', 'like_count',
            'collect_count', 'comment_count', 'publish_time', 'audit_status',
            'audit_time', 'is_deleted', 'is_liked', 'is_collected'
        ]
        read_only_fields = [
            'recommend_id', 'like_count', 'collect_count', 'comment_count',
            'publish_time', 'audit_time', 'is_deleted'
        ]

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Like.objects.filter(
                openid=request.user,
                recommend_id=obj.recommend_id
            ).exists()
        return False

    def get_is_collected(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Collect.objects.filter(
                openid=request.user,
                stall_id=obj.stall_id
            ).exists()
        return False


class RecommendCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recommend
        fields = [
            'stall_id', 'dish_id', 'images', 'content', 'tags'
        ]

    def validate_images(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('图片必须是数组')
        if len(value) > 9:  # 限制最多9张图片
            raise serializers.ValidationError('图片不能超过9张')
        return value

    def validate_content(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError('推荐文案至少5个字符')
        return value

    def validate_tags(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('标签必须是数组')
        if len(value) > 5:  # 限制最多5个标签
            raise serializers.ValidationError('标签不能超过5个')
        return value


class RecommendListSerializer(serializers.ModelSerializer):
    user_info = UserSerializer(source='openid', read_only=True)
    stall_name = serializers.CharField(source='stall_id.stall_name', read_only=True)
    canteen_name = serializers.CharField(source='stall_id.canteen_id.canteen_name', read_only=True)
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Recommend
        fields = [
            'recommend_id', 'user_info', 'stall_name', 'canteen_name',
            'images', 'content', 'tags', 'like_count', 'collect_count',
            'comment_count', 'publish_time', 'is_liked'
        ]

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Like.objects.filter(
                openid=request.user,
                recommend_id=obj.recommend_id
            ).exists()
        return False


class LikeSerializer(serializers.ModelSerializer):
    user_info = UserSerializer(source='openid', read_only=True)
    recommend_content = serializers.CharField(source='recommend_id.content', read_only=True)

    class Meta:
        model = Like
        fields = ['id', 'openid', 'user_info', 'recommend_id', 'recommend_content', 'like_time']
        read_only_fields = ['id', 'like_time']


class CollectSerializer(serializers.ModelSerializer):
    user_info = UserSerializer(source='openid', read_only=True)
    stall_info = StallSimpleSerializer(source='stall_id', read_only=True)

    class Meta:
        model = Collect
        fields = ['id', 'openid', 'user_info', 'stall_id', 'stall_info', 'collect_time']
        read_only_fields = ['id', 'collect_time']


class CheckinSerializer(serializers.ModelSerializer):
    user_info = UserSerializer(source='openid', read_only=True)
    stall_info = StallSimpleSerializer(source='stall_id', read_only=True)

    class Meta:
        model = Checkin
        fields = [
            'checkin_id', 'openid', 'user_info', 'stall_id', 'stall_info',
            'rating', 'comment', 'checkin_time'
        ]
        read_only_fields = ['checkin_id', 'checkin_time']


class CheckinCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Checkin
        fields = ['stall_id', 'rating', 'comment']

    def validate_rating(self, value):
        if value < 1.0 or value > 5.0:
            raise serializers.ValidationError('评分必须在1.0到5.0之间')
        return value


class CommentSerializer(serializers.ModelSerializer):
    user_info = UserSerializer(source='openid', read_only=True)
    reply_user_info = UserSerializer(source='reply_to.openid', read_only=True)

    class Meta:
        model = Comment
        fields = [
            'comment_id', 'openid', 'user_info', 'recommend_id', 'content',
            'reply_to', 'reply_user_info', 'create_time', 'is_deleted'
        ]
        read_only_fields = ['comment_id', 'create_time', 'is_deleted']


class CommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['recommend_id', 'content', 'reply_to']

    def validate_content(self, value):
        if len(value.strip()) < 1:
            raise serializers.ValidationError('评论内容不能为空')
        if len(value) > 200:
            raise serializers.ValidationError('评论内容不能超过200个字符')
        return value


class RecommendStatsSerializer(serializers.Serializer):
    total_recommends = serializers.IntegerField()
    total_likes = serializers.IntegerField()
    total_collects = serializers.IntegerField()
    total_comments = serializers.IntegerField()
    total_checkins = serializers.IntegerField()
    avg_rating = serializers.FloatField()