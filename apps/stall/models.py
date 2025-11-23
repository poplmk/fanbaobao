from django.db import models

# Create your models here.
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.utils.helpers import generate_id


class Stall(models.Model):
    stall_id = models.CharField(max_length=8, primary_key=True, verbose_name='档口ID')
    canteen_id = models.ForeignKey(
        'canteen.Canteen',
        on_delete=models.CASCADE,
        db_column='canteen_id',
        verbose_name='所属食堂'
    )
    stall_name = models.CharField(max_length=30, verbose_name='档口名称')
    stall_image = models.JSONField(default=list, verbose_name='档口轮播图URL数组')
    window_location = models.CharField(max_length=20, blank=True, null=True, verbose_name='窗口位置')
    business_hours = models.CharField(max_length=100, verbose_name='营业时间')
    payment_method = models.JSONField(default=list, verbose_name='支付方式数组')
    tags = models.JSONField(default=list, verbose_name='核心标签数组')
    praise_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='好评率'
    )
    popularity_value = models.IntegerField(default=0, verbose_name='热度值')
    is_active = models.SmallIntegerField(default=1, choices=((1, '营业中'), (0, '已关闭')), verbose_name='是否营业')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'stall'
        verbose_name = '档口'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['canteen_id']),
            models.Index(fields=['stall_name']),
            models.Index(fields=['is_active']),
            models.Index(fields=['praise_rate']),
            models.Index(fields=['popularity_value']),
            models.Index(fields=['create_time']),
        ]

    def __str__(self):
        return f'{self.stall_name}({self.canteen_id.canteen_name})'

    def save(self, *args, **kwargs):
        if not self.stall_id:
            # 生成档口ID: st + 食堂ID后3位 + 3位序列号
            canteen_suffix = self.canteen_id.canteen_id[-3:] if self.canteen_id else '001'
            last_stall = Stall.objects.filter(
                canteen_id=self.canteen_id
            ).order_by('-stall_id').first()

            if last_stall:
                sequence = int(last_stall.stall_id[-3:]) + 1
            else:
                sequence = 1

            self.stall_id = f'st{canteen_suffix}{sequence:03d}'

        super().save(*args, **kwargs)

        # 更新食堂的档口数量
        if self.canteen_id:
            self.canteen_id.update_stall_count()

    def update_popularity(self):
        """更新热度值"""
        from apps.recommend.models import Checkin, Collect
        from apps.recommend.models import Like, Comment

        # 计算打卡次数
        checkin_count = Checkin.objects.filter(stall_id=self.stall_id).count()

        # 计算收藏次数
        collect_count = Collect.objects.filter(stall_id=self.stall_id).count()

        # 计算推荐内容相关的互动
        from apps.recommend.models import Recommend
        recommend_stalls = Recommend.objects.filter(stall_id=self.stall_id)
        like_count = Like.objects.filter(recommend_id__in=recommend_stalls).count()
        comment_count = Comment.objects.filter(recommend_id__in=recommend_stalls).count()

        # 计算热度值 (权重可调整)
        self.popularity_value = (
                checkin_count * 3 +
                collect_count * 2 +
                like_count * 1 +
                comment_count * 1
        )
        self.save()

    def update_praise_rate(self):
        """更新好评率"""
        from apps.recommend.models import Checkin
        checkins = Checkin.objects.filter(stall_id=self.stall_id)

        if checkins.exists():
            avg_rating = checkins.aggregate(models.Avg('rating'))['rating__avg']
            self.praise_rate = round(avg_rating * 20, 2)  # 5分制转百分制
        else:
            self.praise_rate = 0

        self.save()