import time
import json
import logging
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from .response import UnauthorizedResponse
from apps.user.authentication import JWTAuthentication

logger = logging.getLogger(__name__)


class RequestLogMiddleware(MiddlewareMixin):
    """请求日志中间件"""

    def process_request(self, request):
        request.start_time = time.time()

    def process_response(self, request, response):
        # 计算请求耗时
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
        else:
            duration = 0

        # 记录请求日志
        log_data = {
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
            'duration': round(duration, 3),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'ip': self.get_client_ip(request),
        }

        # 添加用户信息（如果已认证）
        if hasattr(request, 'user') and request.user.is_authenticated:
            log_data['user'] = request.user.openid

        logger.info(f"API Request: {json.dumps(log_data)}")

        return response

    def get_client_ip(self, request):
        """获取客户端IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class JWTAuthenticationMiddleware(MiddlewareMixin):
    """JWT认证中间件"""

    def process_request(self, request):
        # 跳过某些路径的认证
        exempt_paths = [
            '/api/auth/login',
            '/api/auth/register',
            '/admin/',
            '/static/',
            '/media/',
        ]

        if any(request.path.startswith(path) for path in exempt_paths):
            return None

        # 进行JWT认证
        authenticator = JWTAuthentication()
        try:
            auth_result = authenticator.authenticate(request)
            if auth_result is not None:
                user, token = auth_result
                request.user = user
                request.auth = token
        except Exception as e:
            # 认证失败，但不立即返回错误，让视图层处理
            pass

        return None


class ExceptionHandlerMiddleware(MiddlewareMixin):
    """全局异常处理中间件"""

    def process_exception(self, request, exception):
        logger.error(f"Unhandled exception: {str(exception)}", exc_info=True)
        return None