from rest_framework import serializers
from .models import Notice, FeedbackType, Feedback, Policy
from apps.user.serializers import UserSerializer


class NoticeSerializer(serializers.ModelSerializer):
    user_info = UserSerializer(source='openid', read_only=True)

    class Meta:
        model = Notice
        fields = [
            'notice_id', 'openid', 'user_info', 'notice_type', 'notice_content',
            'jump_url', 'send_time', 'read_status'
        ]
        read_only_fields = ['notice_id', 'send_time']


class NoticeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notice
        fields = ['openid', 'notice_type', 'notice_content', 'jump_url']


class FeedbackTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackType
        fields = ['feedback_type_id', 'type_name']
        read_only_fields = ['feedback_type_id']


class FeedbackSerializer(serializers.ModelSerializer):
    user_info = UserSerializer(source='openid', read_only=True)
    type_info = FeedbackTypeSerializer(source='feedback_type', read_only=True)

    class Meta:
        model = Feedback
        fields = [
            'feedback_id', 'openid', 'user_info', 'feedback_type', 'type_info',
            'content', 'images', 'submit_time', 'handle_status', 'handle_time', 'reply'
        ]
        read_only_fields = ['feedback_id', 'submit_time', 'handle_time']


class FeedbackCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['feedback_type', 'content', 'images']

    def validate_content(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("反馈内容至少10个字符")
        if len(value) > 200:
            raise serializers.ValidationError("反馈内容不能超过200个字符")
        return value

    def validate_images(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("图片必须是数组")
        if len(value) > 3:
            raise serializers.ValidationError("最多上传3张图片")
        return value


class FeedbackUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['handle_status', 'reply']

    def validate_handle_status(self, value):
        if value not in ['pending', 'processing', 'resolved', 'rejected']:
            raise serializers.ValidationError("无效的处理状态")
        return value


class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = Policy
        fields = ['policy_id', 'policy_name', 'content', 'update_time']
        read_only_fields = ['policy_id', 'update_time']


class PolicyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Policy
        fields = ['policy_name', 'content']

    def validate_content(self, value):
        if len(value.strip()) < 50:
            raise serializers.ValidationError("政策内容至少50个字符")
        return value


class SystemStatsSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    total_notices = serializers.IntegerField()
    total_feedbacks = serializers.IntegerField()
    pending_feedbacks = serializers.IntegerField()
    unread_notices = serializers.IntegerField()