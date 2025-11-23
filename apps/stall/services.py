from django.db.models import Count, Avg, Q
from django.utils import timezone
from django.core.cache import cache
from .models import Stall
from apps.recommend.models import Checkin, Collect
from apps.dish.models import Dish


class StallService:
    """档口服务类"""

    @staticmethod
    def get_nearby_stalls(latitude, longitude, radius=2000):
        """
        获取附近档口（简化版距离计算）
        """
        # 这里简化处理，返回所有营业中的档口
        # 实际项目应该使用地理空间查询
        stalls = Stall.objects.filter(
            is_active=1
        ).select_related('canteen_id')

        # 为每个档口计算大致距离
        for stall in stalls:
            stall.distance = StallService._calculate_distance(
                latitude, longitude,
                float(stall.canteen_id.latitude),
                float(stall.canteen_id.longitude)
            )

        # 过滤在半径内的档口并按距离排序
        nearby_stalls = [stall for stall in stalls if stall.distance <= radius]
        return sorted(nearby_stalls, key=lambda x: x.distance)

    @staticmethod
    def _calculate_distance(lat1, lng1, lat2, lng2):
        """计算两个坐标点之间的距离（米）简化版"""
        # 简化计算，实际项目应该使用精确的地理距离计算
        import math
        lat_diff = (lat2 - lat1) * 111320  # 纬度每度约111km
        lng_diff = (lng2 - lng1) * 111320 * math.cos(math.radians(lat1))
        return math.sqrt(lat_diff ** 2 + lng_diff ** 2)

    @staticmethod
    def get_stall_stats(stall_id):
        """
        获取档口统计信息
        """
        cache_key = f'stall_stats:{stall_id}'
        stats = cache.get(cache_key)

        if stats is None:
            try:
                stall = Stall.objects.get(stall_id=stall_id)

                # 获取打卡统计
                checkin_stats = Checkin.objects.filter(
                    stall_id=stall_id
                ).aggregate(
                    total_checkins=Count('checkin_id'),
                    avg_rating=Avg('rating'),
                    today_checkins=Count('checkin_id', filter=Q(checkin_time__date=timezone.now().date()))
                )

                # 获取收藏统计
                collect_count = Collect.objects.filter(stall_id=stall_id).count()

                # 获取菜品统计
                dish_stats = Dish.objects.filter(
                    stall_id=stall_id
                ).aggregate(
                    total_dishes=Count('dish_id'),
                    special_dishes=Count('dish_id', filter=Q(is_special=1)),
                    sold_out_dishes=Count('dish_id', filter=Q(is_sold_out=1))
                )

                # 获取评分分布
                rating_distribution = Checkin.objects.filter(
                    stall_id=stall_id
                ).values('rating').annotate(count=Count('checkin_id')).order_by('rating')

                stats = {
                    'stall_info': {
                        'name': stall.stall_name,
                        'praise_rate': stall.praise_rate,
                        'popularity': stall.popularity_value
                    },
                    'checkin_stats': checkin_stats,
                    'collect_count': collect_count,
                    'dish_stats': dish_stats,
                    'rating_distribution': list(rating_distribution)
                }

                # 缓存5分钟
                cache.set(cache_key, stats, 300)

            except Stall.DoesNotExist:
                return {}

        return stats

    @staticmethod
    def search_stalls(query, filters=None):
        """
        搜索档口
        """
        if filters is None:
            filters = {}

        queryset = Stall.objects.filter(is_active=1).select_related('canteen_id')

        # 关键词搜索
        if query:
            queryset = queryset.filter(
                Q(stall_name__icontains=query) |
                Q(tags__icontains=query) |
                Q(canteen_id__canteen_name__icontains=query)
            )

        # 食堂筛选
        if filters.get('canteen_id'):
            queryset = queryset.filter(canteen_id=filters['canteen_id'])

        # 标签筛选
        if filters.get('tag'):
            queryset = queryset.filter(tags__contains=[filters['tag']])

        # 评分筛选
        min_rating = filters.get('min_rating')
        if min_rating:
            queryset = queryset.filter(praise_rate__gte=float(min_rating))

        # 排序
        sort_by = filters.get('sort_by', 'popularity')
        if sort_by == 'rating':
            queryset = queryset.order_by('-praise_rate')
        elif sort_by == 'distance' and filters.get('latitude') and filters.get('longitude'):
            # 距离排序需要特殊处理
            pass
        else:
            queryset = queryset.order_by('-popularity_value')

        return queryset

    @staticmethod
    def update_stall_popularity_batch():
        """
        批量更新档口热度值（定时任务）
        """
        stalls = Stall.objects.filter(is_active=1)
        for stall in stalls:
            stall.update_popularity()

    @staticmethod
    def update_stall_ratings_batch():
        """
        批量更新档口评分（定时任务）
        """
        stalls = Stall.objects.filter(is_active=1)
        for stall in stalls:
            stall.update_praise_rate()