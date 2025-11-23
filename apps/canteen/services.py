from django.db.models import Count, Avg
from django.core.cache import cache
from .models import Canteen
from apps.stall.models import Stall
from apps.recommend.models import Checkin
from django.db import models

class CanteenService:
    """食堂服务类"""

    @staticmethod
    def get_nearby_canteens(latitude, longitude, radius=2000):
        """
        获取附近食堂（简化版距离计算）
        实际项目中应该使用地理空间查询
        """
        # 这里简化处理，返回所有食堂
        # 实际项目应该使用PostGIS或类似技术进行地理空间查询
        canteens = Canteen.objects.filter(is_active=1)

        # 为每个食堂计算大致距离（简化版）
        for canteen in canteens:
            # 简化距离计算，实际应该使用Haversine公式
            canteen.distance = CanteenService._calculate_distance(
                latitude, longitude,
                float(canteen.latitude), float(canteen.longitude)
            )

        # 按距离排序
        return sorted(canteens, key=lambda x: x.distance)

    @staticmethod
    def _calculate_distance(lat1, lng1, lat2, lng2):
        """计算两个坐标点之间的距离（公里）简化版"""
        # 简化计算，实际项目应该使用精确的地理距离计算
        return abs(lat1 - lat2) + abs(lng1 - lng2)

    @staticmethod
    def get_canteen_stats(canteen_id):
        """
        获取食堂统计信息
        """
        cache_key = f'canteen_stats:{canteen_id}'
        stats = cache.get(cache_key)

        if stats is None:
            try:
                canteen = Canteen.objects.get(canteen_id=canteen_id)

                # 获取档口统计
                stall_stats = Stall.objects.filter(
                    canteen_id=canteen_id
                ).aggregate(
                    total_stalls=Count('stall_id'),
                    active_stalls=Count('stall_id', filter=models.Q(is_active=1)),
                    avg_rating=Avg('praise_rate')
                )

                # 获取打卡统计
                checkin_stats = Checkin.objects.filter(
                    stall_id__canteen_id=canteen_id
                ).aggregate(
                    total_checkins=Count('checkin_id'),
                    avg_rating=Avg('rating')
                )

                stats = {
                    'canteen_info': {
                        'name': canteen.canteen_name,
                        'stall_count': canteen.stall_count,
                        'business_hours': canteen.business_hours
                    },
                    'stall_stats': stall_stats,
                    'checkin_stats': checkin_stats
                }

                # 缓存5分钟
                cache.set(cache_key, stats, 300)

            except Canteen.DoesNotExist:
                return {}

        return stats