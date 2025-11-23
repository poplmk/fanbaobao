from rest_framework import serializers
from .models import Stall
from apps.canteen.serializers import CanteenListSerializer


class StallSerializer(serializers.ModelSerializer):
    canteen_info = CanteenListSerializer(source='canteen_id', read_only=True)
    is_collected = serializers.SerializerMethodField()

    class Meta:
        model = Stall
        fields = [
            'stall_id', 'canteen_id', 'canteen_info', 'stall_name', 'stall_image',
            'window_location', 'business_hours', 'payment_method', 'tags',
            'praise_rate', 'popularity_value', 'is_active', 'create_time',
            'update_time', 'is_collected'
        ]
        read_only_fields = ['stall_id', 'praise_rate', 'popularity_value', 'create_time', 'update_time']

    def get_is_collected(self, obj):
        """获取当前用户是否收藏了该档口"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            from apps.recommend.models import Collect
            return Collect.objects.filter(
                openid=request.user,
                stall_id=obj.stall_id
            ).exists()
        return False


class StallCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stall
        fields = [
            'canteen_id', 'stall_name', 'stall_image', 'window_location',
            'business_hours', 'payment_method', 'tags', 'is_active'
        ]


class StallListSerializer(serializers.ModelSerializer):
    canteen_name = serializers.CharField(source='canteen_id.canteen_name', read_only=True)
    canteen_icon = serializers.URLField(source='canteen_id.canteen_icon', read_only=True)
    is_collected = serializers.SerializerMethodField()
    today_checkins = serializers.SerializerMethodField()

    class Meta:
        model = Stall
        fields = [
            'stall_id', 'stall_name', 'stall_image', 'canteen_name', 'canteen_icon',
            'window_location', 'business_hours', 'tags', 'praise_rate',
            'popularity_value', 'is_active', 'is_collected', 'today_checkins'
        ]

    def get_is_collected(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            from apps.recommend.models import Collect
            return Collect.objects.filter(
                openid=request.user,
                stall_id=obj.stall_id
            ).exists()
        return False

    def get_today_checkins(self, obj):
        """获取今日打卡次数"""
        from django.utils import timezone
        from apps.recommend.models import Checkin
        today = timezone.now().date()
        return Checkin.objects.filter(
            stall_id=obj.stall_id,
            checkin_time__date=today
        ).count()


class StallSimpleSerializer(serializers.ModelSerializer):
    canteen_name = serializers.CharField(source='canteen_id.canteen_name', read_only=True)

    class Meta:
        model = Stall
        fields = [
            'stall_id', 'stall_name', 'canteen_name', 'stall_image',
            'praise_rate', 'popularity_value', 'is_active'
        ]


class StallUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stall
        fields = [
            'stall_name', 'stall_image', 'window_location', 'business_hours',
            'payment_method', 'tags', 'is_active'
        ]

    def validate_stall_image(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('档口图片必须是数组')
        if len(value) > 10:  # 限制最多10张图片
            raise serializers.ValidationError('档口图片不能超过10张')
        return value

    def validate_payment_method(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('支付方式必须是数组')
        valid_methods = ['wechat', 'alipay', 'card', 'cash']
        for method in value:
            if method not in valid_methods:
                raise serializers.ValidationError(f'无效的支付方式: {method}')
        return value