from django.db.models import Q, Count
from django.utils import timezone
from django.core.cache import cache
from .models import Friend, FriendApply
from apps.user.models import User, UserPrefer
from apps.recommend.models import Recommend, Like


class FriendService:
    """好友服务类"""

    @staticmethod
    def send_friend_apply(applicant, receiver, apply_msg=''):
        """
        发送好友申请
        """
        # 检查是否已经是好友
        if Friend.objects.filter(
                user_openid=applicant,
                friend_openid=receiver
        ).exists():
            raise ValueError("你们已经是好友了")

        # 检查是否有待处理的申请
        pending_apply = FriendApply.objects.filter(
            applicant_openid=applicant,
            receiver_openid=receiver,
            apply_status='pending'
        ).first()

        if pending_apply:
            raise ValueError("已发送过好友申请，请等待对方处理")

        # 检查对方是否已向你发送申请
        reverse_apply = FriendApply.objects.filter(
            applicant_openid=receiver,
            receiver_openid=applicant,
            apply_status='pending'
        ).first()

        if reverse_apply:
            # 直接接受对方的申请
            reverse_apply.accept()
            raise ValueError("对方已向你发送好友申请，已自动接受")

        # 创建新的申请
        apply = FriendApply.objects.create(
            applicant_openid=applicant,
            receiver_openid=receiver,
            apply_msg=apply_msg
        )

        return apply

    @staticmethod
    def add_friend_directly(user, friend, remark_name=''):
        """
        直接添加好友（用于测试或特殊情况）
        """
        if Friend.objects.filter(
                user_openid=user,
                friend_openid=friend
        ).exists():
            raise ValueError("你们已经是好友了")

        # 创建双向好友关系
        friend_relation1 = Friend.objects.create(
            user_openid=user,
            friend_openid=friend,
            remark_name=remark_name
        )

        Friend.objects.create(
            user_openid=friend,
            friend_openid=user
        )

        return friend_relation1

    @staticmethod
    def remove_friend(user, friend):
        """
        删除好友（双向删除）
        """
        Friend.objects.filter(
            user_openid=user,
            friend_openid=friend
        ).delete()

        Friend.objects.filter(
            user_openid=friend,
            friend_openid=user
        ).delete()

    @staticmethod
    def get_online_friends(user):
        """
        获取在线好友（简化版）
        """
        # 实际项目中应该基于WebSocket连接状态判断
        five_minutes_ago = timezone.now() - timezone.timedelta(minutes=5)

        return Friend.objects.filter(
            user_openid=user,
            last_active_time__gte=five_minutes_ago
        ).select_related('friend_openid').order_by('-last_active_time')

    @staticmethod
    def search_users(query, current_user, limit=20):
        """
        搜索用户（用于添加好友）
        """
        users = User.objects.filter(
            Q(nickname__icontains=query) |
            Q(openid__icontains=query)
        ).exclude(
            openid=current_user.openid  # 排除自己
        ).exclude(
            # 排除已经是好友的用户
            openid__in=Friend.objects.filter(
                user_openid=current_user
            ).values_list('friend_openid', flat=True)
        )[:limit]

        return users

    @staticmethod
    def get_friend_recommendations(user, limit=10):
        """
        获取好友推荐
        """
        cache_key = f'friend_recommendations_detail:{user.openid}'
        recommendations = cache.get(cache_key)

        if recommendations is None:
            recommendations = []

            # 1. 基于共同好友推荐
            common_friend_recommendations = FriendService._get_common_friend_recommendations(user, limit // 2)
            recommendations.extend(common_friend_recommendations)

            # 2. 基于共同兴趣推荐
            common_interest_recommendations = FriendService._get_common_interest_recommendations(user, limit // 2)
            recommendations.extend(common_interest_recommendations)

            # 去重
            seen_users = set()
            unique_recommendations = []

            for rec in recommendations:
                if rec['user'].openid not in seen_users:
                    seen_users.add(rec['user'].openid)
                    unique_recommendations.append(rec)

            recommendations = unique_recommendations[:limit]

            # 缓存30分钟
            cache.set(cache_key, recommendations, 1800)

        return recommendations

    @staticmethod
    def _get_common_friend_recommendations(user, limit):
        """
        基于共同好友的推荐
        """
        # 获取用户的好友
        user_friends = Friend.objects.filter(user_openid=user).values_list('friend_openid', flat=True)

        if not user_friends:
            return []

        # 找到好友的好友（排除已经是好友的用户）
        friend_of_friends = Friend.objects.filter(
            user_openid__in=user_friends
        ).exclude(
            friend_openid=user
        ).exclude(
            friend_openid__in=user_friends
        ).values('friend_openid').annotate(
            common_friends=Count('user_openid')
        ).order_by('-common_friends')[:limit]

        recommendations = []
        for item in friend_of_friends:
            try:
                recommended_user = User.objects.get(openid=item['friend_openid'])
                recommendations.append({
                    'user': recommended_user,
                    'reason': f'有 {item["common_friends"]} 个共同好友',
                    'common_friends_count': item['common_friends'],
                    'common_interests': []
                })
            except User.DoesNotExist:
                continue

        return recommendations

    @staticmethod
    def _get_common_interest_recommendations(user, limit):
        """
        基于共同兴趣的推荐
        """
        try:
            user_prefer = UserPrefer.objects.get(openid=user)
        except UserPrefer.DoesNotExist:
            return []

        # 获取有相似偏好的用户
        similar_users = UserPrefer.objects.filter(
            openid__is_active=True
        ).exclude(
            openid=user
        ).exclude(
            # 排除已经是好友的用户
            openid__in=Friend.objects.filter(user_openid=user).values_list('friend_openid', flat=True)
        )

        recommendations = []
        for similar_user_prefer in similar_users[:limit]:
            common_interests = []

            # 比较口味偏好
            user_tastes = set(user_prefer.taste_prefer.keys())
            similar_tastes = set(similar_user_prefer.taste_prefer.keys())
            common_tastes = user_tastes & similar_tastes
            if common_tastes:
                common_interests.extend(list(common_tastes)[:3])

            # 比较食堂偏好
            user_canteens = set(user_prefer.target_canteen.keys())
            similar_canteens = set(similar_user_prefer.target_canteen.keys())
            common_canteens = user_canteens & similar_canteens
            if common_canteens:
                common_interests.extend([f"都喜欢{canteen}" for canteen in list(common_canteens)[:2]])

            if common_interests:
                recommendations.append({
                    'user': similar_user_prefer.openid,
                    'reason': '有共同的美食偏好',
                    'common_friends_count': 0,
                    'common_interests': common_interests
                })

        return recommendations

    @staticmethod
    def get_friend_stats(user):
        """
        获取好友统计信息
        """
        total_friends = Friend.objects.filter(user_openid=user).count()

        # 在线好友（简化判断）
        five_minutes_ago = timezone.now() - timezone.timedelta(minutes=5)
        online_friends = Friend.objects.filter(
            user_openid=user,
            last_active_time__gte=five_minutes_ago
        ).count()

        pending_applications = FriendApply.objects.filter(
            receiver_openid=user,
            apply_status='pending'
        ).count()

        sent_applications = FriendApply.objects.filter(
            applicant_openid=user,
            apply_status='pending'
        ).count()

        return {
            'total_friends': total_friends,
            'online_friends': online_friends,
            'pending_applications': pending_applications,
            'sent_applications': sent_applications
        }

    @staticmethod
    def get_common_friends(user1, user2):
        """
        获取两个用户的共同好友
        """
        user1_friends = Friend.objects.filter(
            user_openid=user1
        ).values_list('friend_openid', flat=True)

        user2_friends = Friend.objects.filter(
            user_openid=user2
        ).values_list('friend_openid', flat=True)

        common_friend_ids = set(user1_friends) & set(user2_friends)

        return User.objects.filter(openid__in=common_friend_ids)

    @staticmethod
    def calculate_friendship_degree(user1, user2):
        """
        计算好友亲密度
        """
        degree = 0

        # 1. 共同好友数量（权重：5）
        common_friends = FriendService.get_common_friends(user1, user2)
        degree += len(common_friends) * 5

        # 2. 互相点赞数量（权重：3）
        mutual_likes = Like.objects.filter(
            openid=user1,
            recommend_id__openid=user2
        ).count() + Like.objects.filter(
            openid=user2,
            recommend_id__openid=user1
        ).count()
        degree += mutual_likes * 3

        # 3. 成为好友的时间（权重：2）
        try:
            friendship = Friend.objects.get(user_openid=user1, friend_openid=user2)
            days_friends = (timezone.now() - friendship.create_time).days
            degree += min(days_friends, 365) * 2  # 最多365天
        except Friend.DoesNotExist:
            pass

        # 4. 最近互动频率（权重：1）
        one_month_ago = timezone.now() - timezone.timedelta(days=30)
        recent_interactions = Like.objects.filter(
            Q(openid=user1, recommend_id__openid=user2) |
            Q(openid=user2, recommend_id__openid=user1),
            like_time__gte=one_month_ago
        ).count()
        degree += min(recent_interactions, 50)  # 最多50次

        return min(degree, 100)  # 最大100分

    @staticmethod
    def update_user_active_time(user):
        """
        更新用户活跃时间
        """
        # 更新用户自己的好友关系中的活跃时间
        Friend.objects.filter(user_openid=user).update(last_active_time=timezone.now())

        # 更新用户作为好友的关系中的活跃时间
        Friend.objects.filter(friend_openid=user).update(last_active_time=timezone.now())

    @staticmethod
    def cleanup_expired_applications():
        """
        清理过期申请（定时任务）
        """
        from datetime import timedelta
        expired_time = timezone.now() - timedelta(days=7)

        expired_applications = FriendApply.objects.filter(
            apply_status='pending',
            apply_time__lt=expired_time
        )

        count = expired_applications.update(apply_status='expired')
        return count