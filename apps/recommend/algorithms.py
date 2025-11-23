import math
from django.db.models import Count, Q
from django.core.cache import cache
from .models import Recommend, Like
from apps.user.models import UserPrefer


class RecommendationAlgorithm:
    """推荐算法类"""

    @staticmethod
    def collaborative_filtering(user, limit=10):
        """
        协同过滤推荐
        """
        # 获取用户点赞过的内容
        user_likes = Like.objects.filter(openid=user).values_list('recommend_id', flat=True)

        if not user_likes:
            return []

        # 找到有相似点赞行为的用户
        similar_users = Like.objects.filter(
            recommend_id__in=user_likes
        ).exclude(
            openid=user
        ).values('openid').annotate(
            common_likes=Count('recommend_id')
        ).order_by('-common_likes')[:10]

        similar_user_ids = [item['openid'] for item in similar_users]

        if not similar_user_ids:
            return []

        # 获取相似用户点赞但当前用户未点赞的内容
        recommendations = Recommend.objects.filter(
            like__openid__in=similar_user_ids,
            audit_status='approved',
            is_deleted=0
        ).exclude(
            recommend_id__in=user_likes
        ).annotate(
            score=Count('like')
        ).order_by('-score', '-publish_time')[:limit]

        return recommendations

    @staticmethod
    def content_based_filtering(user, limit=10):
        """
        基于内容的推荐
        """
        try:
            user_prefer = UserPrefer.objects.get(openid=user)
        except UserPrefer.DoesNotExist:
            return []

        # 基于用户偏好计算内容相似度
        recommendations = Recommend.objects.filter(
            audit_status='approved',
            is_deleted=0
        ).exclude(
            openid=user  # 排除用户自己的内容
        )

        scored_recommendations = []
        for rec in recommendations:
            score = RecommendationAlgorithm._calculate_content_similarity(rec, user_prefer)
            if score > 0:
                scored_recommendations.append((rec, score))

        # 按分数排序并返回
        scored_recommendations.sort(key=lambda x: x[1], reverse=True)
        return [rec for rec, score in scored_recommendations[:limit]]

    @staticmethod
    def _calculate_content_similarity(recommendation, user_prefer):
        """
        计算内容与用户偏好的相似度
        """
        score = 0

        # 基于口味偏好
        taste_prefer = user_prefer.taste_prefer
        if taste_prefer and recommendation.tags:
            common_tastes = set(taste_prefer.keys()) & set(recommendation.tags)
            score += len(common_tastes) * 2

        # 基于目标食堂
        target_canteen = user_prefer.target_canteen
        if target_canteen and recommendation.stall_id.canteen_id.canteen_id in target_canteen:
            score += 3

        # 基于食材偏好
        ingredient_prefer = user_prefer.ingredient_prefer
        if ingredient_prefer and recommendation.dish_id and recommendation.dish_id.ingredient:
            common_ingredients = set(ingredient_prefer.keys()) & set(recommendation.dish_id.ingredient)
            score += len(common_ingredients)

        # 排除忌口食材
        forbidden_ingredient = user_prefer.forbidden_ingredient
        if forbidden_ingredient and recommendation.dish_id and recommendation.dish_id.ingredient:
            forbidden_common = set(forbidden_ingredient.keys()) & set(recommendation.dish_id.ingredient)
            if forbidden_common:
                score = -10  # 严重扣分

        return score

    @staticmethod
    def hybrid_recommendation(user, limit=10):
        """
        混合推荐算法
        """
        # 获取协同过滤结果
        cf_recommendations = RecommendationAlgorithm.collaborative_filtering(user, limit // 2)

        # 获取基于内容的推荐结果
        cb_recommendations = RecommendationAlgorithm.content_based_filtering(user, limit // 2)

        # 合并结果并去重
        all_recommendations = {}

        for rec in cf_recommendations:
            all_recommendations[rec.recommend_id] = rec

        for rec in cb_recommendations:
            if rec.recommend_id not in all_recommendations:
                all_recommendations[rec.recommend_id] = rec

        # 如果结果不足，用热门推荐补充
        if len(all_recommendations) < limit:
            remaining = limit - len(all_recommendations)
            hot_recommendations = Recommend.objects.filter(
                audit_status='approved',
                is_deleted=0
            ).exclude(
                recommend_id__in=all_recommendations.keys()
            ).order_by('-like_count', '-publish_time')[:remaining]

            for rec in hot_recommendations:
                all_recommendations[rec.recommend_id] = rec

        return list(all_recommendations.values())[:limit]