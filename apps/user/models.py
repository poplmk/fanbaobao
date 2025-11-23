from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from apps.utils.helpers import generate_id


class UserManager(BaseUserManager):
    def create_user(self, openid, nickname, **extra_fields):
        if not openid:
            raise ValueError('OpenID必须提供')

        user = self.model(openid=openid, nickname=nickname, **extra_fields)
        user.save(using=self._db)
        return user

    def create_superuser(self, openid, nickname, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(openid, nickname, **extra_fields)


class User(AbstractBaseUser):
    openid = models.CharField(max_length=32, primary_key=True, verbose_name='微信OpenID')
    nickname = models.CharField(max_length=20, verbose_name='用户昵称')
    avatar_url = models.URLField(max_length=255, blank=True, null=True, verbose_name='头像URL')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    last_login_time = models.DateTimeField(auto_now=True, verbose_name='最后登录时间')
    status = models.SmallIntegerField(default=1, choices=((1, '正常'), (0, '禁用')), verbose_name='账号状态')
    version = models.IntegerField(default=0, verbose_name='数据版本号')

    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'openid'
    REQUIRED_FIELDS = ['nickname']

    class Meta:
        db_table = 'user'
        verbose_name = '用户'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['create_time']),
            models.Index(fields=['last_login_time']),
        ]

    def __str__(self):
        return f'{self.nickname}({self.openid})'

    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_superuser


class UserPrefer(models.Model):
    id = models.BigAutoField(primary_key=True, verbose_name='偏好记录ID')
    openid = models.ForeignKey(User, on_delete=models.CASCADE, db_column='openid', verbose_name='关联用户')
    taste_prefer = models.JSONField(default=dict, verbose_name='口味偏好数组')
    ingredient_prefer = models.JSONField(default=dict, verbose_name='食材偏好数组')
    forbidden_ingredient = models.JSONField(default=dict, verbose_name='忌口食材数组')
    target_canteen = models.JSONField(default=dict, verbose_name='意向食堂数组')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'user_prefer'
        verbose_name = '用户偏好'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['openid']),
        ]

    def __str__(self):
        return f'{self.openid.nickname}的偏好设置'