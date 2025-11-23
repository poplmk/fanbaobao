from django.db import models

# Create your models here.
from django.db import models
from apps.utils.helpers import generate_id

class Notice(models.Model):
    NOTICE_TYPE_CHOICES = [
        ('system', '系统通知'),
        ('interaction', '互动通知'),
        ('social', '社交通知'),
        ('recommend', '推荐通知'),
    ]

    notice_id = models.CharField(max_length=12, primary_key=True, verbose_name='通知ID')
    openid = models.ForeignKey(
        'user.User',
        on_delete=models.CASCADE,
        db_column='openid',
        verbose_name='接收用户'
    )
    notice_type = models.CharField(max_length=10, choices=NOTICE_TYPE_CHOICES, verbose_name='通知类型')
    notice_content = models.CharField(max_length=100, verbose_name='通知内容')
    jump_url = models.URLField(max_length=255, blank=True, null=True, verbose_name='跳转链接')
    send_time = models.DateTimeField(auto_now_add=True, verbose_name='发送时间')
    read_status = models.SmallIntegerField(default=0, choices=((1, '已读'), (0, '未读')), verbose_name='已读状态')

    class Meta:
        db_table = 'notice'
        verbose_name = '通知'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['openid']),
            models.Index(fields=['notice_type']),
            models.Index(fields=['read_status']),
            models.Index(fields=['send_time']),
        ]

    def __str__(self):
        return f'{self.notice_type}: {self.notice_content[:20]}'

    def save(self, *args, **kwargs):
        if not self.notice_id:
            self.notice_id = generate_id('nt')
        super().save(*args, **kwargs)

    def mark_as_read(self):
        """标记通知为已读"""
        self.read_status = 1
        self.save()

    @classmethod
    def send_notice(cls, user, notice_type, content, jump_url=None):
        """发送通知"""
        return cls.objects.create(
            openid=user,
            notice_type=notice_type,
            notice_content=content,
            jump_url=jump_url
        )

class FeedbackType(models.Model):
    feedback_type_id = models.CharField(max_length=4, primary_key=True, verbose_name='反馈类型ID')
    type_name = models.CharField(max_length=20, unique=True, verbose_name='类型名称')

    class Meta:
        db_table = 'feedback_type'
        verbose_name = '反馈类型'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.type_name

    def save(self, *args, **kwargs):
        if not self.feedback_type_id:
            self.feedback_type_id = generate_id('ft')
        super().save(*args, **kwargs)

class Feedback(models.Model):
    HANDLE_STATUS_CHOICES = [
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('resolved', '已解决'),
        ('rejected', '不予处理'),
    ]

    feedback_id = models.CharField(max_length=12, primary_key=True, verbose_name='反馈记录ID')
    openid = models.ForeignKey(
        'user.User',
        on_delete=models.CASCADE,
        db_column='openid',
        verbose_name='反馈用户'
    )
    feedback_type = models.ForeignKey(
        FeedbackType,
        on_delete=models.CASCADE,
        db_column='feedback_type',
        verbose_name='反馈类型'
    )
    content = models.CharField(max_length=200, verbose_name='反馈内容')
    images = models.JSONField(default=list, verbose_name='反馈图片数组')
    submit_time = models.DateTimeField(auto_now_add=True, verbose_name='提交时间')
    handle_status = models.CharField(max_length=10, choices=HANDLE_STATUS_CHOICES, default='pending', verbose_name='处理状态')
    handle_time = models.DateTimeField(null=True, blank=True, verbose_name='处理时间')
    reply = models.CharField(max_length=200, blank=True, verbose_name='处理回复')

    class Meta:
        db_table = 'feedback'
        verbose_name = '意见反馈'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['openid']),
            models.Index(fields=['feedback_type']),
            models.Index(fields=['handle_status']),
            models.Index(fields=['submit_time']),
        ]

    def __str__(self):
        return f'{self.openid.nickname}的反馈({self.feedback_id})'

    def save(self, *args, **kwargs):
        if not self.feedback_id:
            self.feedback_id = generate_id('fb')
        super().save(*args, **kwargs)

    def update_status(self, status, reply=''):
        """更新处理状态"""
        from django.utils import timezone
        self.handle_status = status
        self.handle_time = timezone.now()
        if reply:
            self.reply = reply
        self.save()

class Policy(models.Model):
    policy_id = models.CharField(max_length=4, primary_key=True, verbose_name='政策ID')
    policy_name = models.CharField(max_length=20, unique=True, verbose_name='政策名称')
    content = models.TextField(verbose_name='政策正文内容')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'policy'
        verbose_name = '政策内容'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['update_time']),
        ]

    def __str__(self):
        return self.policy_name

    def save(self, *args, **kwargs):
        if not self.policy_id:
            self.policy_id = generate_id('pc')
        super().save(*args, **kwargs)