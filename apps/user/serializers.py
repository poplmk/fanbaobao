from rest_framework import serializers
from .models import User, UserPrefer

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['openid', 'nickname', 'avatar_url', 'create_time', 'last_login_time', 'status']
        read_only_fields = ['openid', 'create_time', 'last_login_time']

class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['openid', 'nickname', 'avatar_url']

class UserPreferSerializer(serializers.ModelSerializer):
    openid = serializers.CharField(source='openid.openid', read_only=True)
    nickname = serializers.CharField(source='openid.nickname', read_only=True)

    class Meta:
        model = UserPrefer
        fields = ['id', 'openid', 'nickname', 'taste_prefer', 'ingredient_prefer',
                 'forbidden_ingredient', 'target_canteen', 'update_time']
        read_only_fields = ['id', 'update_time']

class UserPreferUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPrefer
        fields = ['taste_prefer', 'ingredient_prefer', 'forbidden_ingredient', 'target_canteen']

    def validate_taste_prefer(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('口味偏好必须是JSON对象')
        return value

    def validate_ingredient_prefer(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('食材偏好必须是JSON对象')
        return value

class UserLoginSerializer(serializers.Serializer):
    code = serializers.CharField(required=True, max_length=100)
    nickname = serializers.CharField(required=False, max_length=20)
    avatar_url = serializers.URLField(required=False, allow_null=True)

    def validate_code(self, value):
        if not value:
            raise serializers.ValidationError('微信code不能为空')
        return value