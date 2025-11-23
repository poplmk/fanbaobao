from django.db import models

# Create your models here.
from django.db import models
from apps.utils.helpers import generate_id

class Canteen(models.Model):
    canteen_id = models.CharField(max_length=6, primary_key=True, verbose_name='食堂ID')
    canteen_name = models.CharField(max_length=20, unique=True, verbose_name='食堂名称')
    canteen_icon = models.URLField(max_length=255, blank=True, null=True, verbose_name='食堂图标URL')
    latitude = models.DecimalField(max_digits=10, decimal_places=6, verbose_name='纬度')
    longitude = models.DecimalField(max_digits=10, decimal_places=6, verbose_name='经度')
    address = models.CharField(max_length=50, verbose_name='详细地址')
    business_hours = models.CharField(max_length=100, verbose_name='营业时间')
    stall_count = models.IntegerField(default=0, verbose_name='档口数量')
    is_active = models.SmallIntegerField(default=1, choices=((1, '启用'), (0, '禁用')), verbose_name='是否启用')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'canteen'
        verbose_name = '食堂'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['canteen_name']),
            models.Index(fields=['is_active']),
            models.Index(fields=['create_time']),
        ]

    def __str__(self):
        return self.canteen_name

    def save(self, *args, **kwargs):
        if not self.canteen_id:
            self.canteen_id = generate_id('ct')
        super().save(*args, **kwargs)

    def update_stall_count(self):
        """更新档口数量"""
        from apps.stall.models import Stall
        self.stall_count = Stall.objects.filter(
            canteen_id=self.canteen_id,
            is_active=1
        ).count()
        self.save()