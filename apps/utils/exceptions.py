from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException
from rest_framework import status
from rest_framework.response import Response
from django.db import DatabaseError
from redis import RedisError
import logging

logger = logging.getLogger(__name__)


class BaseAPIException(APIException):
    """基础API异常"""

    def __init__(self, detail=None, code=None):
        super().__init__(detail=detail, code=code)
        self.code = code or status.HTTP_400_BAD_REQUEST


class BusinessException(BaseAPIException):
    """业务异常"""
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, message, code=400):
        super().__init__(detail=message, code=code)


class AuthenticationException(BaseAPIException):
    """认证异常"""
    status_code = status.HTTP_401_UNAUTHORIZED

    def __init__(self, message='认证失败', code=401):
        super().__init__(detail=message, code=code)


class PermissionException(BaseAPIException):
    """权限异常"""
    status_code = status.HTTP_403_FORBIDDEN

    def __init__(self, message='权限不足', code=403):
        super().__init__(detail=message, code=code)


class NotFoundException(BaseAPIException):
    """未找到异常"""
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, message='资源未找到', code=404):
        super().__init__(detail=message, code=code)


def custom_exception_handler(exc, context):
    """自定义异常处理器"""

    # 调用DRF默认异常处理器
    response = exception_handler(exc, context)

    if response is not None:
        # 处理DRF内置异常
        if isinstance(exc, APIException):
            response.data = {
                'code': response.status_code,
                'message': str(exc.detail),
                'data': None
            }
    else:
        # 处理非DRF异常
        view = context.get('view')
        request = context.get('request')

        if isinstance(exc, DatabaseError) or isinstance(exc, RedisError):
            # 数据库异常
            logger.error(f'数据库异常: {str(exc)}', exc_info=True)
            response_data = {
                'code': 500,
                'message': '数据库服务异常',
                'data': None
            }
            response = Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            # 其他未处理异常
            logger.error(f'未处理异常: {str(exc)}', exc_info=True)
            response_data = {
                'code': 500,
                'message': '服务器内部错误',
                'data': None
            }
            response = Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response