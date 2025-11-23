import jwt
import json
from django.conf import settings
from django.utils import timezone
from django.db.models import Q, Max, Count, Subquery, OuterRef
from django.core.cache import cache
from .models import Chat
from apps.user.models import User
from apps.social.models import Friend


class ChatService:
    """聊天服务类"""

    @staticmethod
    def send_message(sender, receiver, msg_type, msg_content):
        """
        发送消息
        """
        # 检查是否好友关系（可选，根据业务需求）
        if not Friend.objects.filter(
                user_openid=sender,
                friend_openid=receiver
        ).exists():
            raise ValueError("只能向好友发送消息")

        # 创建消息
        message = Chat.objects.create(
            sender_openid=sender,
            receiver_openid=receiver,
            msg_type=msg_type,
            msg_content=msg_content
        )

        # 更新发送者的活跃时间
        Friend.objects.filter(
            user_openid=sender,
            friend_openid=receiver
        ).update(last_active_time=timezone.now())

        return message

    @staticmethod
    def get_user_conversations(user):
        """
        获取用户的所有对话列表
        """
        cache_key = f'user_conversations:{user.openid}'
        conversations = cache.get(cache_key)

        if conversations is None:
            # 获取用户参与的所有对话的最新消息
            latest_messages_subquery = Chat.objects.filter(
                Q(sender_openid=user) | Q(receiver_openid=user),
                is_deleted=0
            ).filter(
                Q(sender_openid=OuterRef('pk')) | Q(receiver_openid=OuterRef('pk'))
            ).order_by('-send_time').values('send_time')[:1]

            # 获取对话伙伴
            sent_to = User.objects.filter(
                received_messages__sender_openid=user,
                received_messages__is_deleted=0
            ).distinct()

            received_from = User.objects.filter(
                sent_messages__receiver_openid=user,
                sent_messages__is_deleted=0
            ).distinct()

            # 合并并去重
            conversation_partners = (sent_to | received_from).distinct()

            conversations = []
            for partner in conversation_partners:
                # 获取最后一条消息
                last_message = Chat.objects.filter(
                    (
                            (Q(sender_openid=user) & Q(receiver_openid=partner)) |
                            (Q(sender_openid=partner) & Q(receiver_openid=user))
                    ),
                    is_deleted=0
                ).order_by('-send_time').first()

                # 获取未读消息数量
                unread_count = Chat.objects.filter(
                    sender_openid=partner,
                    receiver_openid=user,
                    read_status=0,
                    is_deleted=0
                ).count()

                # 检查在线状态（简化版）
                is_online = ChatService._is_user_online(partner)

                conversations.append({
                    'user': partner,
                    'last_message': last_message.get_message_summary() if last_message else '',
                    'last_message_time': last_message.send_time if last_message else timezone.now(),
                    'unread_count': unread_count,
                    'is_online': is_online
                })

            # 按最后消息时间排序
            conversations.sort(key=lambda x: x['last_message_time'], reverse=True)

            # 缓存5分钟
            cache.set(cache_key, conversations, 300)

        return conversations

    @staticmethod
    def _is_user_online(user):
        """
        检查用户是否在线（简化版）
        """
        # 实际项目中应该基于WebSocket连接状态判断
        five_minutes_ago = timezone.now() - timezone.timedelta(minutes=5)

        # 检查好友关系中最后活跃时间
        recent_activity = Friend.objects.filter(
            user_openid=user,
            last_active_time__gte=five_minutes_ago
        ).exists()

        return recent_activity

    @staticmethod
    def get_share_content(user, content_type, limit=10):
        """
        获取可分享的内容
        """
        share_content = []

        if content_type == 'stall':
            # 获取用户收藏的档口
            from apps.recommend.models import Collect
            from apps.stall.serializers import StallSimpleSerializer

            collected_stalls = Collect.objects.filter(
                openid=user
            ).select_related('stall_id').order_by('-collect_time')[:limit]

            for collect in collected_stalls:
                serializer = StallSimpleSerializer(collect.stall_id)
                share_content.append({'stall': serializer.data})

        elif content_type == 'dish':
            # 获取用户最近打卡的档口的菜品
            from apps.recommend.models import Checkin
            from apps.dish.models import Dish
            from apps.dish.serializers import DishSimpleSerializer

            recent_checkins = Checkin.objects.filter(
                openid=user
            ).select_related('stall_id').order_by('-checkin_time')[:5]

            stall_ids = [checkin.stall_id.stall_id for checkin in recent_checkins]

            dishes = Dish.objects.filter(
                stall_id__in=stall_ids,
                is_sold_out=0
            ).select_related('stall_id').order_by('-is_special')[:limit]

            for dish in dishes:
                serializer = DishSimpleSerializer(dish)
                share_content.append({'dish': serializer.data})

        elif content_type == 'recommend':
            # 获取用户点赞的推荐内容
            from apps.recommend.models import Like
            from apps.recommend.serializers import RecommendListSerializer

            liked_recommends = Like.objects.filter(
                openid=user
            ).select_related('recommend_id').order_by('-like_time')[:limit]

            for like in liked_recommends:
                serializer = RecommendListSerializer(like.recommend_id)
                share_content.append({'recommend': serializer.data})

        return share_content

    @staticmethod
    def search_messages(user, query, limit=50):
        """
        搜索消息
        """
        return Chat.objects.filter(
            (
                    (Q(sender_openid=user) | Q(receiver_openid=user)) &
                    Q(msg_content__icontains=query) &
                    Q(is_deleted=0)
            )
        ).select_related('sender_openid', 'receiver_openid').order_by('-send_time')[:limit]

    @staticmethod
    def get_chat_stats(user):
        """
        获取聊天统计信息
        """
        total_messages = Chat.objects.filter(
            Q(sender_openid=user) | Q(receiver_openid=user),
            is_deleted=0
        ).count()

        unread_messages = Chat.get_unread_count(user)

        # 活跃对话数量（最近7天有消息的对话）
        seven_days_ago = timezone.now() - timezone.timedelta(days=7)
        active_conversations = Chat.objects.filter(
            (Q(sender_openid=user) | Q(receiver_openid=user)),
            send_time__gte=seven_days_ago,
            is_deleted=0
        ).values('sender_openid', 'receiver_openid').distinct().count()

        return {
            'total_messages': total_messages,
            'unread_messages': unread_messages,
            'active_conversations': active_conversations
        }

    @staticmethod
    def clear_conversation(user, partner):
        """
        清空与某个用户的对话（软删除）
        """
        deleted_count = Chat.objects.filter(
            (
                    (Q(sender_openid=user) & Q(receiver_openid=partner)) |
                    (Q(sender_openid=partner) & Q(receiver_openid=user))
            ),
            is_deleted=0
        ).update(is_deleted=1)

        return deleted_count

    @staticmethod
    def generate_websocket_token(user):
        """
        生成WebSocket连接令牌
        """
        payload = {
            'openid': user.openid,
            'nickname': user.nickname,
            'exp': timezone.now() + timezone.timedelta(hours=24),
            'iat': timezone.now()
        }

        token = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm='HS256'
        )

        return token

    @staticmethod
    def update_user_online_status(user, is_online):
        """
        更新用户在线状态
        """
        cache_key = f'user_online:{user.openid}'

        if is_online:
            # 设置在线状态，有效期5分钟
            cache.set(cache_key, True, 300)

            # 更新好友关系中的活跃时间
            Friend.objects.filter(user_openid=user).update(last_active_time=timezone.now())
            Friend.objects.filter(friend_openid=user).update(last_active_time=timezone.now())
        else:
            # 移除在线状态
            cache.delete(cache_key)

    @staticmethod
    def is_user_online(user):
        """
        检查用户是否在线
        """
        return cache.get(f'user_online:{user.openid}', False)

    @staticmethod
    def get_online_friends(user):
        """
        获取在线好友
        """
        friends = Friend.objects.filter(user_openid=user).select_related('friend_openid')
        online_friends = []

        for friend in friends:
            if ChatService.is_user_online(friend.friend_openid):
                online_friends.append(friend.friend_openid)

        return online_friends

    @staticmethod
    def process_shared_content(msg_type, msg_content):
        """
        处理分享内容的消息
        """
        if msg_type in ['stall_share', 'dish_share', 'recommend_share']:
            try:
                content_data = json.loads(msg_content)
                return content_data
            except json.JSONDecodeError:
                return {'error': '无效的分享内容'}

        return {'text': msg_content}