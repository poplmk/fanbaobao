from django.db.models import Count, Q
from django.utils import timezone
from django.core.cache import cache
from .models import Notice, Feedback, Policy
from apps.user.models import User


class SystemService:
    """系统服务类"""

    @staticmethod
    def get_system_overview():
        """
        获取系统概览统计
        """
        total_users = User.objects.filter(status=1).count()
        total_notices = Notice.objects.count()
        total_feedbacks = Feedback.objects.count()
        pending_feedbacks = Feedback.objects.filter(handle_status='pending').count()
        unread_notices = Notice.objects.filter(read_status=0).count()

        return {
            'total_users': total_users,
            'total_notices': total_notices,
            'total_feedbacks': total_feedbacks,
            'pending_feedbacks': pending_feedbacks,
            'unread_notices': unread_notices
        }

    @staticmethod
    def get_user_stats(user):
        """
        获取用户个人统计
        """
        from apps.recommend.models import Recommend, Like, Collect, Checkin
        from apps.social.models import Friend

        total_recommends = Recommend.objects.filter(openid=user).count()
        total_likes = Like.objects.filter(openid=user).count()
        total_collects = Collect.objects.filter(openid=user).count()
        total_checkins = Checkin.objects.filter(openid=user).count()
        total_friends = Friend.objects.filter(user_openid=user).count()
        unread_notices = Notice.objects.filter(openid=user, read_status=0).count()

        return {
            'total_recommends': total_recommends,
            'total_likes': total_likes,
            'total_collects': total_collects,
            'total_checkins': total_checkins,
            'total_friends': total_friends,
            'unread_notices': unread_notices
        }

    @staticmethod
    def send_notification_to_users(notice_type, content, jump_url=None, target_users=None):
        """
        向用户发送通知
        """
        valid_types = ['system', 'interaction', 'social', 'recommend']
        if notice_type not in valid_types:
            raise ValueError("无效的通知类型")

        if target_users:
            # 向指定用户发送
            users = User.objects.filter(openid__in=target_users, status=1)
        else:
            # 向所有活跃用户发送
            users = User.objects.filter(status=1)

        sent_count = 0
        for user in users:
            Notice.objects.create(
                openid=user,
                notice_type=notice_type,
                notice_content=content,
                jump_url=jump_url
            )
            sent_count += 1

        return sent_count

    @staticmethod
    def get_notification_templates():
        """
        获取通知模板
        """
        return {
            'system': [
                {
                    'name': '系统维护通知',
                    'content': '系统将于{时间}进行维护，预计耗时{时长}，期间服务可能不可用。',
                    'variables': ['时间', '时长']
                },
                {
                    'name': '版本更新通知',
                    'content': '应用已更新至版本{版本号}，新增了{功能描述}，修复了若干问题。',
                    'variables': ['版本号', '功能描述']
                }
            ],
            'interaction': [
                {
                    'name': '点赞通知',
                    'content': '{用户昵称}点赞了你的推荐内容',
                    'variables': ['用户昵称']
                },
                {
                    'name': '评论通知',
                    'content': '{用户昵称}评论了你的推荐内容：{评论内容}',
                    'variables': ['用户昵称', '评论内容']
                }
            ],
            'social': [
                {
                    'name': '好友申请通知',
                    'content': '{用户昵称}向你发送了好友申请',
                    'variables': ['用户昵称']
                },
                {
                    'name': '好友接受通知',
                    'content': '{用户昵称}接受了你的好友申请',
                    'variables': ['用户昵称']
                }
            ]
        }

    @staticmethod
    def send_interaction_notification(recipient, notice_type, content, jump_url=None):
        """
        发送互动通知
        """
        return Notice.send_notice(recipient, 'interaction', content, jump_url)

    @staticmethod
    def send_social_notification(recipient, content, jump_url=None):
        """
        发送社交通知
        """
        return Notice.send_notice(recipient, 'social', content, jump_url)

    @staticmethod
    def process_feedback_batch(feedback_ids, status, reply_template=''):
        """
        批量处理反馈
        """
        feedbacks = Feedback.objects.filter(feedback_id__in=feedback_ids)

        processed_count = 0
        for feedback in feedbacks:
            reply = reply_template.format(用户昵称=feedback.openid.nickname)
            feedback.update_status(status, reply)
            processed_count += 1

        return processed_count

    @staticmethod
    def get_feedback_analysis(days=30):
        """
        获取反馈分析数据
        """
        start_date = timezone.now() - timezone.timedelta(days=days)

        # 反馈类型分布
        type_distribution = Feedback.objects.filter(
            submit_time__gte=start_date
        ).values('feedback_type__type_name').annotate(
            count=Count('feedback_id')
        ).order_by('-count')

        # 处理状态分布
        status_distribution = Feedback.objects.filter(
            submit_time__gte=start_date
        ).values('handle_status').annotate(
            count=Count('feedback_id')
        )

        # 每日反馈数量
        daily_feedbacks = Feedback.objects.filter(
            submit_time__gte=start_date
        ).extra({
            'date': "DATE(submit_time)"
        }).values('date').annotate(
            count=Count('feedback_id')
        ).order_by('date')

        return {
            'type_distribution': list(type_distribution),
            'status_distribution': list(status_distribution),
            'daily_feedbacks': list(daily_feedbacks),
            'period': f'最近{days}天'
        }

    @staticmethod
    def cleanup_old_notices(days=90):
        """
        清理旧通知（定时任务）
        """
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        deleted_count = Notice.objects.filter(
            send_time__lt=cutoff_date,
            read_status=1  # 只删除已读的通知
        ).delete()[0]

        return deleted_count

    @staticmethod
    def get_policy_content(policy_name):
        """
        获取政策内容
        """
        try:
            policy = Policy.objects.get(policy_name=policy_name)
            return policy.content
        except Policy.DoesNotExist:
            return None

    @staticmethod
    def update_policy(policy_name, content):
        """
        更新政策内容
        """
        policy, created = Policy.objects.update_or_create(
            policy_name=policy_name,
            defaults={'content': content}
        )
        return policy