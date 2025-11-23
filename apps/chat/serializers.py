from rest_framework import serializers
from .models import Chat
from apps.user.serializers import UserSerializer
from apps.stall.serializers import StallSimpleSerializer
from apps.dish.serializers import DishSimpleSerializer
from apps.recommend.serializers import RecommendListSerializer


class ChatSerializer(serializers.ModelSerializer):
    sender_info = UserSerializer(source='sender_openid', read_only=True)
    receiver_info = UserSerializer(source='receiver_openid', read_only=True)
    message_summary = serializers.SerializerMethodField()
    is_own_message = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = [
            'id', 'sender_openid', 'sender_info', 'receiver_openid', 'receiver_info',
            'msg_type', 'msg_content', 'send_time', 'read_status', 'is_deleted',
            'message_summary', 'is_own_message'
        ]
        read_only_fields = ['id', 'send_time', 'is_deleted']

    def get_message_summary(self, obj):
        return obj.get_message_summary()

    def get_is_own_message(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.sender_openid == request.user
        return False


class ChatCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = ['receiver_openid', 'msg_type', 'msg_content']

    def validate_receiver_openid(self, value):
        # 检查是否尝试向自己发送消息
        request = self.context.get('request')
        if request and value == request.user:
            raise serializers.ValidationError("不能向自己发送消息")
        return value

    def validate_msg_content(self, value):
        if not value.strip():
            raise serializers.ValidationError("消息内容不能为空")
        if len(value) > 500:
            raise serializers.ValidationError("消息内容不能超过500个字符")
        return value

    def validate_msg_type(self, value):
        valid_types = ['text', 'image', 'stall_share', 'dish_share', 'recommend_share']
        if value not in valid_types:
            raise serializers.ValidationError(f"不支持的消息类型: {value}")
        return value


class ChatListSerializer(serializers.ModelSerializer):
    sender_info = UserSerializer(source='sender_openid', read_only=True)
    receiver_info = UserSerializer(source='receiver_openid', read_only=True)
    message_summary = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = [
            'id', 'sender_info', 'receiver_info', 'msg_type', 'msg_content',
            'send_time', 'read_status', 'message_summary'
        ]

    def get_message_summary(self, obj):
        return obj.get_message_summary()


class ConversationPartnerSerializer(serializers.Serializer):
    user_info = UserSerializer(source='user', read_only=True)
    last_message = serializers.CharField()
    last_message_time = serializers.DateTimeField()
    unread_count = serializers.IntegerField()
    is_online = serializers.BooleanField()


class ShareContentSerializer(serializers.Serializer):
    stall = StallSimpleSerializer(required=False)
    dish = DishSimpleSerializer(required=False)
    recommend = RecommendListSerializer(required=False)


class ChatStatsSerializer(serializers.Serializer):
    total_messages = serializers.IntegerField()
    unread_messages = serializers.IntegerField()
    active_conversations = serializers.IntegerField()