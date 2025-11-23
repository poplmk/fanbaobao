from django.db.models import Count, Avg, Q
from django.utils import timezone
from django.core.cache import cache
from .models import Recommend, Like, Collect, Checkin, Comment
from apps.user.models import UserPrefer


class RecommendService:
    """推荐服务类"""

    @staticmethod
    def get_personalized_recommendations(user, limit=20):
        """
        获取个性化推荐内容
        """
        cache_key = f'personalized_recommendations:{user.openid}'
        recommendations = cache.get(cache_key)

        if recommendations is None:
            base_queryset = Recommend.objects.filter(
                audit_status='approved',
                is_deleted=0
            ).select_related(
                'openid', 'stall_id', 'stall_id__canteen_id', 'dish_id'
            )

            try:
                user_prefer = UserPrefer.objects.get(openid=user)
                recommendations = RecommendService._get_recommendations_by_preference(
                    base_queryset, user_prefer, limit
                )
            except UserPrefer.DoesNotExist:
                # 如果没有用户偏好，返回热门推荐
                recommendations = base_queryset.order_by(
                    '-like_count', '-comment_count', '-publish_time'
                )[:limit]

            # 缓存10分钟
            cache.set(cache_key, list(recommendations), 600)

        return recommendations

    @staticmethod
    def _get_recommendations_by_preference(queryset, user_prefer, limit):
        """
        基于用户偏好获取推荐内容
        """
        # 基于口味偏好
        taste_prefer = user_prefer.taste_prefer
        if taste_prefer:
            # 这里可以实现更复杂的推荐算法
            for taste in taste_prefer:
                queryset = queryset.filter(tags__contains=[taste])

        # 基于目标食堂
        target_canteen = user_prefer.target_canteen
        if target_canteen:
            canteen_ids = list(target_canteen.keys())
            queryset = queryset.filter(stall_id__canteen_id__in=canteen_ids)

        # 排除忌口食材相关的推荐
        forbidden_ingredient = user_prefer.forbidden_ingredient
        if forbidden_ingredient:
            for ingredient in forbidden_ingredient:
                queryset = queryset.exclude(
                    Q(dish_id__ingredient__contains=[ingredient]) |
                    Q(tags__contains=[ingredient])
                )

        return queryset.order_by('-like_count', '-publish_time')[:limit]

    @staticmethod
    def get_system_stats():
        """
        获取推荐系统统计信息
        """
        total_recommends = Recommend.objects.filter(
            audit_status='approved',
            is_deleted=0
        ).count()

        total_likes = Like.objects.count()
        total_collects = Collect.objects.count()
        total_comments = Comment.objects.filter(is_deleted=0).count()
        total_checkins = Checkin.objects.count()

        avg_rating = Checkin.objects.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0

        return {
            'total_recommends': total_recommends,
            'total_likes': total_likes,
            'total_collects': total_collects,
            'total_comments': total_comments,
            'total_checkins': total_checkins,
            'avg_rating': round(avg_rating, 1)
        }

    @staticmethod
    def get_trending_recommendations(limit=10):
        """
        获取趋势推荐（最近24小时热门）
        """
        cache_key = 'trending_recommendations'
        trending = cache.get(cache_key)

        if trending is None:
            yesterday = timezone.now() - timezone.timedelta(days=1)

            trending = Recommend.objects.filter(
                audit_status='approved',
                is_deleted=0,
                publish_time__gte=yesterday
            ).select_related(
                'openid', 'stall_id', 'stall_id__canteen_id'
            ).annotate(
                engagement_score=Count('like') + Count('comment') * 2
            ).order_by('-engagement_score', '-publish_time')[:limit]

            # 缓存15分钟
            cache.set(cache_key, list(trending), 900)

        return trending

    @staticmethod
    def audit_recommendation(recommend_id, status, audit_notes=None):
        """
        审核推荐内容
        """
        try:
            recommendation = Recommend.objects.get(recommend_id=recommend_id)
            recommendation.audit_status = status
            recommendation.audit_time = timezone.now()
            recommendation.save()
            return True
        except Recommend.DoesNotExist:
            return False

    @staticmethod
    def batch_update_recommendation_stats():
        """
        批量更新推荐内容统计（定时任务）
        """
        recommendations = Recommend.objects.filter(
            audit_status='approved',
            is_deleted=0
        )

        for recommendation in recommendations:
            # 更新点赞数
            recommendation.like_count = Like.objects.filter(
                recommend_id=recommendation
            ).count()

            # 更新收藏数（通过档口收藏）
            recommendation.collect_count = Collect.objects.filter(
                stall_id=recommendation.stall_id
            ).count()

            # 更新评论数
            recommendation.comment_count = Comment.objects.filter(
                recommend_id=recommendation,
                is_deleted=0
            ).count()

            recommendation.save()