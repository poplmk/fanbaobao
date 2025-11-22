import jwt
from django.conf import settings
from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed
from .models import User


class JWTAuthentication(authentication.BaseAuthentication):
    """JWT认证类"""

    def authenticate(self, request):
        # 从请求头获取token
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header or not auth_header.startswith('Bearer '):
            return None

        token = auth_header[7:]  # 去掉 'Bearer ' 前缀

        try:
            # 解码token
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256']
            )

            # 获取用户
            openid = payload.get('openid')
            if not openid:
                raise AuthenticationFailed('无效的token')

            try:
                user = User.objects.get(openid=openid)
            except User.DoesNotExist:
                raise AuthenticationFailed('用户不存在')

            # 检查用户状态
            if user.status != 1:
                raise AuthenticationFailed('用户已被禁用')

            return (user, token)

        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('token已过期')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('无效的token')
        except Exception as e:
            raise AuthenticationFailed('认证失败')

    def authenticate_header(self, request):
        return 'Bearer realm="api"'