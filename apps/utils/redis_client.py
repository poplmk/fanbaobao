import json
import pickle
from django.core.cache import cache
from django.conf import settings
from .helpers import CustomJSONEncoder


class RedisClient:
    """Redis客户端封装类"""

    @staticmethod
    def set(key, value, timeout=None):
        """
        设置缓存
        """
        if timeout is None:
            timeout = settings.REDIS_DEFAULT_TIMEOUT

        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False, cls=CustomJSONEncoder)
            return cache.set(key, value, timeout)
        except Exception:
            return False

    @staticmethod
    def get(key, default=None):
        """
        获取缓存
        """
        try:
            value = cache.get(key)
            if value is None:
                return default

            # 尝试解析JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception:
            return default

    @staticmethod
    def delete(key):
        """
        删除缓存
        """
        try:
            return cache.delete(key)
        except Exception:
            return False

    @staticmethod
    def exists(key):
        """
        检查键是否存在
        """
        try:
            return cache.has_key(key)
        except Exception:
            return False

    @staticmethod
    def incr(key, amount=1):
        """
        自增
        """
        try:
            return cache.incr(key, amount)
        except Exception:
            return None

    @staticmethod
    def decr(key, amount=1):
        """
        自减
        """
        try:
            return cache.decr(key, amount)
        except Exception:
            return None

    @staticmethod
    def hset(key, field, value):
        """
        设置哈希字段
        """
        try:
            current_data = RedisClient.hgetall(key) or {}
            current_data[field] = value
            return RedisClient.set(key, current_data)
        except Exception:
            return False

    @staticmethod
    def hget(key, field, default=None):
        """
        获取哈希字段
        """
        try:
            data = RedisClient.get(key, {})
            return data.get(field, default)
        except Exception:
            return default

    @staticmethod
    def hgetall(key):
        """
        获取所有哈希字段
        """
        return RedisClient.get(key, {})

    @staticmethod
    def hdel(key, field):
        """
        删除哈希字段
        """
        try:
            data = RedisClient.get(key, {})
            if field in data:
                del data[field]
                return RedisClient.set(key, data)
            return True
        except Exception:
            return False

    @staticmethod
    def sadd(key, *values):
        """
        向集合添加元素
        """
        try:
            current_set = set(RedisClient.get(key, []))
            current_set.update(values)
            return RedisClient.set(key, list(current_set))
        except Exception:
            return False

    @staticmethod
    def srem(key, *values):
        """
        从集合移除元素
        """
        try:
            current_set = set(RedisClient.get(key, []))
            current_set.difference_update(values)
            return RedisClient.set(key, list(current_set))
        except Exception:
            return False

    @staticmethod
    def smembers(key):
        """
        获取集合所有元素
        """
        return set(RedisClient.get(key, []))

    @staticmethod
    def sismember(key, value):
        """
        检查元素是否在集合中
        """
        return value in RedisClient.smembers(key)

    @staticmethod
    def lpush(key, *values):
        """
        向左推入列表
        """
        try:
            current_list = RedisClient.get(key, [])
            current_list = list(values) + current_list
            return RedisClient.set(key, current_list)
        except Exception:
            return False

    @staticmethod
    def rpush(key, *values):
        """
        向右推入列表
        """
        try:
            current_list = RedisClient.get(key, [])
            current_list.extend(values)
            return RedisClient.set(key, current_list)
        except Exception:
            return False

    @staticmethod
    def lrange(key, start=0, end=-1):
        """
        获取列表范围
        """
        try:
            current_list = RedisClient.get(key, [])
            return current_list[start:end]
        except Exception:
            return []

    @staticmethod
    def lpop(key):
        """
        从左弹出元素
        """
        try:
            current_list = RedisClient.get(key, [])
            if current_list:
                value = current_list.pop(0)
                RedisClient.set(key, current_list)
                return value
            return None
        except Exception:
            return None

    @staticmethod
    def rpop(key):
        """
        从右弹出元素
        """
        try:
            current_list = RedisClient.get(key, [])
            if current_list:
                value = current_list.pop()
                RedisClient.set(key, current_list)
                return value
            return None
        except Exception:
            return None

    @staticmethod
    def expire(key, timeout):
        """
        设置过期时间
        """
        try:
            return cache.touch(key, timeout)
        except Exception:
            return False

    @staticmethod
    def ttl(key):
        """
        获取剩余过期时间
        """
        try:
            return cache.ttl(key)
        except Exception:
            return 0

    @staticmethod
    def clear_pattern(pattern):
        """
        清除匹配模式的键
        """
        try:
            # 注意：这个方法在生产环境慎用，可能会影响性能
            keys = cache.keys(pattern)
            for key in keys:
                cache.delete(key)
            return len(keys)
        except Exception:
            return 0

    @staticmethod
    def get_stats():
        """
        获取Redis统计信息
        """
        try:
            # 这里可以添加自定义的统计逻辑
            return {
                'backend': str(cache._cache),
                'key_count': 'N/A'  # 实际项目中可能需要更复杂的统计
            }
        except Exception:
            return {'error': '无法获取统计信息'}