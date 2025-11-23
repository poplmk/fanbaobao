from django.db import models

# Create your models here.
from django.db import models
from apps.utils.helpers import generate_id

class Chat(models.Model):
    MESSAGE_TYPE_CHOICES = [
        ('text', '文本'),
        ('image', '图片'),
        ('stall_share', '档口分享'),
        ('dish_share', '菜品分享'),
        ('recommend_share', '推荐分享'),
    ]

    id = models.BigAutoField(primary_key=True, verbose_name='会话记录ID')
    sender_openid = models.ForeignKey(
        'user.User',
        on_delete=models.CASCADE,
        db_column='sender_openid',
        related_name='sent_messages',
        verbose_name='发送者'
    )
    receiver_openid = models.ForeignKey(
        'user.User',
        on_delete=models.CASCADE,
        db_column='receiver_openid',
        related_name='received_messages',
        verbose_name='接收者'
    )
    msg_type = models.CharField(max_length=10, choices=MESSAGE_TYPE_CHOICES, default='text', verbose_name='消息类型')
    msg_content = models.TextField(max_length=500, verbose_name='消息内容')
    send_time = models.DateTimeField(auto_now_add=True, verbose_name='发送时间')
    read_status = models.SmallIntegerField(default=0, choices=((1, '已读'), (0, '未读')), verbose_name='已读状态')
    is_deleted = models.SmallIntegerField(default=0, choices=((1, '是'), (0, '否')), verbose_name='是否删除')

    class Meta:
        db_table = 'chat'
        verbose_name = '单聊会话'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['sender_openid', 'receiver_openid']),
            models.Index(fields=['receiver_openid', 'sender_openid']),
            models.Index(fields=['send_time']),
            models.Index(fields=['read_status']),
            models.Index(fields=['is_deleted']),
        ]

    def __str__(self):
        return f'{self.sender_openid.nickname} -> {self.receiver_openid.nickname}: {self.msg_content[:20]}'

    def save(self, *args, **kwargs):
        # 确保不会向自己发送消息
        if self.sender_openid == self.receiver_openid:
            raise ValueError("不能向自己发送消息")
        super().save(*args, **kwargs)

    def mark_as_read(self):
        """标记消息为已读"""
        self.read_status = 1
        self.save()

    def get_message_summary(self):
        """获取消息摘要"""
        if self.msg_type == 'text':
            return self.msg_content
        elif self.msg_type == 'image':
            return '[图片]'
        elif self.msg_type == 'stall_share':
            return '[档口分享]'
        elif self.msg_type == 'dish_share':
            return '[菜品分享]'
        elif self.msg_type == 'recommend_share':
            return '[推荐分享]'
        return '[未知消息]'

    @classmethod
    def get_conversation(cls, user1, user2, limit=50, offset=0):
        """获取两个用户之间的对话"""
        return cls.objects.filter(
            (
                (models.Q(sender_openid=user1) & models.Q(receiver_openid=user2)) |
                (models.Q(sender_openid=user2) & models.Q(receiver_openid=user1))
            ),
            is_deleted=0
        ).select_related('sender_openid', 'receiver_openid').order_by('-send_time')[offset:offset+limit]

    @classmethod
    def get_unread_count(cls, user):
        """获取用户的未读消息数量"""
        return cls.objects.filter(
            receiver_openid=user,
            read_status=0,
            is_deleted=0
        ).count()

    @classmethod
    def mark_conversation_as_read(cls, user1, user2):
        """标记与某个用户的对话为已读"""
        cls.objects.filter(
            sender_openid=user2,
            receiver_openid=user1,
            read_status=0,
            is_deleted=0
        ).update(read_status=1)