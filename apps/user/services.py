import jwt
import requests
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from apps.utils.exceptions import BusinessException
from apps.utils.helpers import generate_id
from .models import User, UserPrefer


class UserService:
    """用户服务类"""

    @staticmethod
    def wechat_login(code, nickname=None, avatar_url=None):
        """
        微信登录服务
        """
        # 1. 通过code获取openid
        openid = UserService._get_wechat_openid(code)
        if not openid:
            raise BusinessException('微信登录失败')

        # 2. 查找或创建用户
        user, created = User.objects.get_or_create(
            openid=openid,
            defaults={
                'nickname': nickname or f'用户{openid[-6:]}',
                'avatar_url': avatar_url
            }
        )

        # 3. 更新最后登录时间
        user.last_login_time = timezone.now()
        user.save()

        # 4. 生成JWT token
        token = UserService._generate_jwt_token(user)

        return {
            'user': {
                'openid': user.openid,
                'nickname': user.nickname,
                'avatar_url': user.avatar_url,
                'create_time': user.create_time
            },
            'token': token,
            'is_new_user': created
        }

    @staticmethod
    def _get_wechat_openid(code):
        """
        通过微信code获取openid
        """
        # 这里应该调用微信API，暂时模拟返回
        # 实际项目中需要实现真实的微信API调用
        if not code or code == 'invalid_code':
            return None

        # 模拟返回openid
        return f"mock_openid_{code}"

    @staticmethod
    def _generate_jwt_token(user):
        """
        生成JWT token
        """
        payload = {
            'openid': user.openid,
            'nickname': user.nickname,
            'exp': timezone.now() + settings.JWT_CONFIG['ACCESS_TOKEN_LIFETIME'],
            'iat': timezone.now()
        }

        token = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm='HS256'
        )

        return token

    @staticmethod
    def update_user_preference(openid, preference_data):
        """
        更新用户偏好设置
        """
        try:
            user = User.objects.get(openid=openid)
        except User.DoesNotExist:
            raise BusinessException('用户不存在')

        prefer, created = UserPrefer.objects.update_or_create(
            openid=user,
            defaults=preference_data
        )

        return prefer