from rest_framework.response import Response
from rest_framework import status


class APIResponse(Response):
    """统一API响应格式"""

    def __init__(self, data=None, code=200, message='success',
                 status=status.HTTP_200_OK, headers=None, **kwargs):
        response_data = {
            'code': code,
            'message': message,
            'data': data,
        }
        response_data.update(kwargs)
        super().__init__(data=response_data, status=status, headers=headers)


class SuccessResponse(APIResponse):
    """成功响应"""

    def __init__(self, data=None, message='操作成功', **kwargs):
        super().__init__(data=data, message=message, **kwargs)


class ErrorResponse(APIResponse):
    """错误响应"""

    def __init__(self, message='操作失败', code=400, status=status.HTTP_400_BAD_REQUEST, **kwargs):
        super().__init__(code=code, message=message, status=status, **kwargs)


class NotFoundResponse(APIResponse):
    """未找到响应"""

    def __init__(self, message='资源未找到', code=404, status=status.HTTP_404_NOT_FOUND, **kwargs):
        super().__init__(code=code, message=message, status=status, **kwargs)


class UnauthorizedResponse(APIResponse):
    """未授权响应"""

    def __init__(self, message='未授权访问', code=401, status=status.HTTP_401_UNAUTHORIZED, **kwargs):
        super().__init__(code=code, message=message, status=status, **kwargs)