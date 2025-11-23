from django.db import models

# Create your models here.
from django.db import models
from apps.utils.helpers import generate_id


class Friend(models.Model):
    id = models.BigAutoField(primary_key=True, verbose_name='好友关系ID')
    user_openid = models.ForeignKey(
        'user.User',
        on_delete=models.CASCADE,
        db_column='user_openid',
        related_name='friends_as_user',
        verbose_name='当前用户'
    )
    friend_openid = models.ForeignKey(
        'user.User',
        on_delete=models.CASCADE,
        db_column='friend_openid',
        related_name='friends_as_friend',
        verbose_name='好友用户'
    )
    remark_name = models.CharField(max_length=20, blank=True, verbose_name='备注名')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='成为好友时间')
    last_active_time = models.DateTimeField(auto_now=True, verbose_name='最后活跃时间')

    class Meta:
        db_table = 'friend'
        verbose_name = '好友关系'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['user_openid', 'friend_openid']),
            models.Index(fields=['create_time']),
            models.Index(fields=['last_active_time']),
        ]
        unique_together = [['user_openid', 'friend_openid']]

    def __str__(self):
        return f'{self.user_openid.nickname} -> {self.friend_openid.nickname}'

    def save(self, *args, **kwargs):
        # 确保不会添加自己为好友
        if self.user_openid == self.friend_openid:
            raise ValueError("不能添加自己为好友")
        super().save(*args, **kwargs)

    def get_display_name(self):
        """获取显示名称（优先使用备注名）"""
        return self.remark_name or self.friend_openid.nickname

    def update_active_time(self):
        """更新最后活跃时间"""
        self.last_active_time = models.DateTimeField(auto_now=True)
        self.save()


class FriendApply(models.Model):
    APPLY_STATUS_CHOICES = [
        ('pending', '待处理'),
        ('accepted', '已同意'),
        ('rejected', '已拒绝'),
        ('expired', '已过期'),
    ]

    id = models.BigAutoField(primary_key=True, verbose_name='申请记录ID')
    applicant_openid = models.ForeignKey(
        'user.User',
        on_delete=models.CASCADE,
        db_column='applicant_openid',
        related_name='sent_applications',
        verbose_name='申请人'
    )
    receiver_openid = models.ForeignKey(
        'user.User',
        on_delete=models.CASCADE,
        db_column='receiver_openid',
        related_name='received_applications',
        verbose_name='接收人'
    )
    apply_msg = models.CharField(max_length=50, blank=True, verbose_name='申请留言')
    apply_status = models.CharField(max_length=10, choices=APPLY_STATUS_CHOICES, default='pending',
                                    verbose_name='申请状态')
    apply_time = models.DateTimeField(auto_now_add=True, verbose_name='申请时间')
    handle_time = models.DateTimeField(null=True, blank=True, verbose_name='处理时间')

    class Meta:
        db_table = 'friend_apply'
        verbose_name = '好友申请'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['applicant_openid', 'receiver_openid']),
            models.Index(fields=['apply_status']),
            models.Index(fields=['apply_time']),
        ]
        unique_together = [['applicant_openid', 'receiver_openid']]

    def __str__(self):
        return f'{self.applicant_openid.nickname} -> {self.receiver_openid.nickname}'

    def save(self, *args, **kwargs):
        # 确保不会向自己发送申请
        if self.applicant_openid == self.receiver_openid:
            raise ValueError("不能向自己发送好友申请")
        super().save(*args, **kwargs)

    def accept(self):
        """接受好友申请"""
        if self.apply_status != 'pending':
            raise ValueError("只能处理待处理的申请")

        self.apply_status = 'accepted'
        self.handle_time = models.DateTimeField(auto_now=True)
        self.save()

        # 创建好友关系（双向）
        Friend.objects.get_or_create(
            user_openid=self.applicant_openid,
            friend_openid=self.receiver_openid
        )
        Friend.objects.get_or_create(
            user_openid=self.receiver_openid,
            friend_openid=self.applicant_openid
        )

    def reject(self):
        """拒绝好友申请"""
        if self.apply_status != 'pending':
            raise ValueError("只能处理待处理的申请")

        self.apply_status = 'rejected'
        self.handle_time = models.DateTimeField(auto_now=True)
        self.save()

    def is_expired(self):
        """检查申请是否过期（7天）"""
        from django.utils import timezone
        from datetime import timedelta
        return self.apply_time < timezone.now() - timedelta(days=7)