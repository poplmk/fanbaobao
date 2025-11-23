from rest_framework import serializers
from .models import Friend, FriendApply
from apps.user.serializers import UserSerializer


class FriendSerializer(serializers.ModelSerializer):
    friend_info = UserSerializer(source='friend_openid', read_only=True)
    display_name = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()

    class Meta:
        model = Friend
        fields = [
            'id', 'user_openid', 'friend_openid', 'friend_info',
            'remark_name', 'display_name', 'create_time',
            'last_active_time', 'is_online'
        ]
        read_only_fields = ['id', 'create_time', 'last_active_time']

    def get_display_name(self, obj):
        return obj.get_display_name()

    def get_is_online(self, obj):
        """检查好友是否在线（简化版）"""
        # 实际项目中应该基于WebSocket连接状态或最后活跃时间判断
        from django.utils import timezone
        from datetime import timedelta
        return obj.last_active_time > timezone.now() - timedelta(minutes=5)


class FriendCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Friend
        fields = ['friend_openid', 'remark_name']

    def validate_friend_openid(self, value):
        # 检查是否尝试添加自己
        request = self.context.get('request')
        if request and value == request.user:
            raise serializers.ValidationError("不能添加自己为好友")
        return value


class FriendUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Friend
        fields = ['remark_name']


class FriendApplySerializer(serializers.ModelSerializer):
    applicant_info = UserSerializer(source='applicant_openid', read_only=True)
    receiver_info = UserSerializer(source='receiver_openid', read_only=True)
    can_handle = serializers.SerializerMethodField()

    class Meta:
        model = FriendApply
        fields = [
            'id', 'applicant_openid', 'applicant_info', 'receiver_openid',
            'receiver_info', 'apply_msg', 'apply_status', 'apply_time',
            'handle_time', 'can_handle'
        ]
        read_only_fields = ['id', 'apply_time', 'handle_time']

    def get_can_handle(self, obj):
        """检查当前用户是否可以处理此申请"""
        request = self.context.get('request')
        if request and request.user == obj.receiver_openid and obj.apply_status == 'pending':
            return True
        return False


class FriendApplyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FriendApply
        fields = ['receiver_openid', 'apply_msg']

    def validate_receiver_openid(self, value):
        # 检查是否尝试向自己发送申请
        request = self.context.get('request')
        if request and value == request.user:
            raise serializers.ValidationError("不能向自己发送好友申请")
        return value

    def validate_apply_msg(self, value):
        if value and len(value) > 50:
            raise serializers.ValidationError("申请留言不能超过50个字符")
        return value


class FriendApplyActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['accept', 'reject'])


class FriendRecommendSerializer(serializers.Serializer):
    user_info = UserSerializer(source='user', read_only=True)
    reason = serializers.CharField()
    common_friends_count = serializers.IntegerField()
    common_interests = serializers.ListField(child=serializers.CharField())


class FriendStatsSerializer(serializers.Serializer):
    total_friends = serializers.IntegerField()
    online_friends = serializers.IntegerField()
    pending_applications = serializers.IntegerField()
    sent_applications = serializers.IntegerField()