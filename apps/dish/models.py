from django.db import models

# Create your models here.
from django.db import models
from django.core.validators import MinValueValidator
from apps.utils.helpers import generate_id


class Dish(models.Model):
    dish_id = models.CharField(max_length=10, primary_key=True, verbose_name='菜品ID')
    stall_id = models.ForeignKey(
        'stall.Stall',
        on_delete=models.CASCADE,
        db_column='stall_id',
        verbose_name='所属档口'
    )
    dish_name = models.CharField(max_length=30, verbose_name='菜品名称')
    dish_image = models.URLField(max_length=255, blank=True, null=True, verbose_name='菜品图片URL')
    price = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='价格（元）'
    )
    dish_type = models.CharField(max_length=10, verbose_name='菜品类型')
    taste_tag = models.JSONField(default=list, verbose_name='口味标签数组')
    ingredient = models.JSONField(default=list, verbose_name='主要食材数组')
    is_special = models.SmallIntegerField(default=0, choices=((1, '是'), (0, '否')), verbose_name='是否招牌菜')
    is_sold_out = models.SmallIntegerField(default=0, choices=((1, '是'), (0, '否')), verbose_name='是否售罄')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'dish'
        verbose_name = '菜品'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['stall_id']),
            models.Index(fields=['dish_name']),
            models.Index(fields=['dish_type']),
            models.Index(fields=['price']),
            models.Index(fields=['is_special']),
            models.Index(fields=['is_sold_out']),
            models.Index(fields=['create_time']),
        ]

    def __str__(self):
        return f'{self.dish_name}({self.stall_id.stall_name})'

    def save(self, *args, **kwargs):
        if not self.dish_id:
            # 生成菜品ID: ds + 档口ID后4位 + 2位序列号
            stall_suffix = self.stall_id.stall_id[-4:] if self.stall_id else '0001'
            last_dish = Dish.objects.filter(
                stall_id=self.stall_id
            ).order_by('-dish_id').first()

            if last_dish:
                sequence = int(last_dish.dish_id[-2:]) + 1
            else:
                sequence = 1

            self.dish_id = f'ds{stall_suffix}{sequence:02d}'

        super().save(*args, **kwargs)

    def toggle_sold_out(self):
        """切换售罄状态"""
        self.is_sold_out = 1 if self.is_sold_out == 0 else 0
        self.save()

    def toggle_special(self):
        """切换招牌菜状态"""
        self.is_special = 1 if self.is_special == 0 else 0
        self.save()

    def get_related_recommendations_count(self):
        """获取相关推荐内容数量"""
        from apps.recommend.models import Recommend
        return Recommend.objects.filter(
            dish_id=self.dish_id,
            audit_status='approved',
            is_deleted=0
        ).count()

    def get_average_rating(self):
        """获取平均评分（通过打卡记录计算）"""
        from apps.recommend.models import Checkin
        checkins = Checkin.objects.filter(stall_id=self.stall_id)
        if checkins.exists():
            avg_rating = checkins.aggregate(models.Avg('rating'))['rating__avg']
            return round(avg_rating, 1)
        return 0.0