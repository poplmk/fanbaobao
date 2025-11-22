import json
import hashlib
import uuid
from datetime import datetime, date
from decimal import Decimal
from django.core.serializers.json import DjangoJSONEncoder


class CustomJSONEncoder(DjangoJSONEncoder):
    """自定义JSON编码器"""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')
        elif isinstance(obj, Decimal):
            return float(obj)
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)


def generate_id(prefix=''):
    """生成唯一ID"""
    unique_id = str(uuid.uuid4()).replace('-', '')[:16]
    return f"{prefix}{unique_id}" if prefix else unique_id


def md5_hash(text):
    """生成MD5哈希"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def format_timestamp(timestamp):
    """格式化时间戳"""
    if isinstance(timestamp, (int, float)):
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    return timestamp


def safe_json_loads(json_str, default=None):
    """安全地解析JSON字符串"""
    if default is None:
        default = {}
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(obj, default=None):
    """安全地序列化为JSON字符串"""
    if default is None:
        default = {}
    try:
        return json.dumps(obj, ensure_ascii=False, cls=CustomJSONEncoder)
    except (TypeError, ValueError):
        return json.dumps(default, ensure_ascii=False, cls=CustomJSONEncoder)


def paginate_data(data, page, page_size):
    """手动分页数据"""
    if not data:
        return [], 0

    total = len(data)
    start = (page - 1) * page_size
    end = start + page_size

    paginated_data = data[start:end]
    return paginated_data, total