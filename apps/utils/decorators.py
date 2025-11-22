from functools import wraps
# from django.utils.decorators import available_attrs
from django.core.cache import cache
from rest_framework import status
from .response import ErrorResponse
import time

def available_attrs(fn):
    return tuple(fn.__code__.co_varnames[:fn.__code__.co_argcount])
def rate_limit(key_func=None, rate='100/hour', block_time=60):
    """
    频率限制装饰器
    :param key_func: 生成限制键的函数
    :param rate: 频率限制，如 '100/hour', '10/minute'
    :param block_time: 超过限制后的阻塞时间（秒）
    """

    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            # 生成限制键
            if key_func:
                limit_key = key_func(request)
            else:
                limit_key = f"rate_limit:{request.META.get('REMOTE_ADDR')}:{view_func.__name__}"

            # 检查是否被阻塞
            block_key = f"{limit_key}:block"
            if cache.get(block_key):
                return ErrorResponse(
                    message='请求过于频繁，请稍后再试',
                    code=429,
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )

            # 解析频率限制
            count, period = rate.split('/')
            count = int(count)

            if period == 'second':
                window = 1
            elif period == 'minute':
                window = 60
            elif period == 'hour':
                window = 3600
            elif period == 'day':
                window = 86400
            else:
                window = 3600

            # 使用滑动窗口算法
            current_time = int(time.time())
            window_key = f"{limit_key}:{current_time // window}"
            requests = cache.get(window_key, 0)

            if requests >= count:
                # 设置阻塞
                cache.set(block_key, True, block_time)
                return ErrorResponse(
                    message='请求过于频繁，请稍后再试',
                    code=429,
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )

            # 增加计数
            cache.set(window_key, requests + 1, window)

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def validate_params(required_params=None, optional_params=None):
    """
    参数验证装饰器
    :param required_params: 必需参数列表
    :param optional_params: 可选参数列表
    """

    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            if required_params:
                missing_params = []
                for param in required_params:
                    if param not in request.data and param not in request.GET:
                        missing_params.append(param)

                if missing_params:
                    return ErrorResponse(
                        message=f'缺少必需参数: {", ".join(missing_params)}',
                        code=400
                    )

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def cache_response(timeout=300, key_func=None):
    """
    缓存响应装饰器
    :param timeout: 缓存超时时间（秒）
    :param key_func: 生成缓存键的函数
    """

    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(request, *args, **kwargs)
            else:
                cache_key = f"view_cache:{request.path}:{request.META.get('QUERY_STRING', '')}"

            # 尝试从缓存获取
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                return cached_response

            # 执行视图函数
            response = view_func(request, *args, **kwargs)

            # 缓存响应
            if response.status_code == 200:
                cache.set(cache_key, response, timeout)

            return response

        return _wrapped_view

    return decorator