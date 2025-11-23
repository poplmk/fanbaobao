from django.db import models

# Create your models here.
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.utils.helpers import generate_id


class Tag(models.Model):
    tag_id = models.CharField(max_length=6, primary_key=True, verbose_name='标签ID')
    tag_name = models.CharField(max_length=10, unique=True, verbose_name='标签名称')
    tag_type = models.CharField(max_length=10, verbose_name='标签类型')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'tag'
        verbose_name = '标签'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['tag_type']),
            models.Index(fields=['create_time']),
        ]

    def __str__(self):
        return f'{self.tag_name}({self.tag_type})'

    def save(self, *args, **kwargs):
        if not self.tag_id:
            self.tag_id = generate_id('tag')
        super().save(*args, **kwargs)


class Recommend(models.Model):
    AUDIT_STATUS_CHOICES = [
        ('pending', '待审核'),
        ('approved', '审核通过'),
        ('rejected', '审核不通过'),
    ]

    recommend_id = models.CharField(max_length=12, primary_key=True, verbose_name='推荐记录ID')
    openid = models.ForeignKey('user.User', on_delete=models.CASCADE, db_column='openid', verbose_name='发布用户')
    stall_id = models.ForeignKey('stall.Stall', on_delete=models.CASCADE, db_column='stall_id', verbose_name='关联档口')
    dish_id = models.ForeignKey('dish.Dish', on_delete=models.SET_NULL, null=True, blank=True, db_column='dish_id',
                                verbose_name='关联菜品')
    images = models.JSONField(default=list, verbose_name='推荐图片数组')
    content = models.CharField(max_length=50, verbose_name='推荐文案')
    tags = models.JSONField(default=list, verbose_name='推荐标签数组')
    like_count = models.IntegerField(default=0, verbose_name='点赞数')
    collect_count = models.IntegerField(default=0, verbose_name='收藏数')
    comment_count = models.IntegerField(default=0, verbose_name='评论数')
    publish_time = models.DateTimeField(auto_now_add=True, verbose_name='发布时间')
    audit_status = models.CharField(max_length=10, choices=AUDIT_STATUS_CHOICES, default='pending',
                                    verbose_name='审核状态')
    audit_time = models.DateTimeField(null=True, blank=True, verbose_name='审核时间')
    is_deleted = models.SmallIntegerField(default=0, choices=((1, '是'), (0, '否')), verbose_name='是否删除')

    class Meta:
        db_table = 'recommend'
        verbose_name = '推荐内容'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['openid']),
            models.Index(fields=['stall_id']),
            models.Index(fields=['dish_id']),
            models.Index(fields=['audit_status']),
            models.Index(fields=['publish_time']),
            models.Index(fields=['is_deleted']),
        ]

    def __str__(self):
        return f'{self.openid.nickname}的推荐({self.recommend_id})'

    def save(self, *args, **kwargs):
        if not self.recommend_id:
            self.recommend_id = generate_id('rec')
        super().save(*args, **kwargs)

    def increment_like_count(self):
        """增加点赞数"""
        self.like_count += 1
        self.save()

    def decrement_like_count(self):
        """减少点赞数"""
        self.like_count = max(0, self.like_count - 1)
        self.save()

    def increment_collect_count(self):
        """增加收藏数"""
        self.collect_count += 1
        self.save()

    def decrement_collect_count(self):
        """减少收藏数"""
        self.collect_count = max(0, self.collect_count - 1)
        self.save()

    def increment_comment_count(self):
        """增加评论数"""
        self.comment_count += 1
        self.save()

    def decrement_comment_count(self):
        """减少评论数"""
        self.comment_count = max(0, self.comment_count - 1)
        self.save()


class Like(models.Model):
    id = models.BigAutoField(primary_key=True, verbose_name='点赞记录ID')
    openid = models.ForeignKey('user.User', on_delete=models.CASCADE, db_column='openid', verbose_name='点赞用户')
    recommend_id = models.ForeignKey(Recommend, on_delete=models.CASCADE, db_column='recommend_id',
                                     verbose_name='关联推荐')
    like_time = models.DateTimeField(auto_now_add=True, verbose_name='点赞时间')

    class Meta:
        db_table = 'like'
        verbose_name = '点赞'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['openid', 'recommend_id']),
            models.Index(fields=['like_time']),
        ]
        unique_together = [['openid', 'recommend_id']]

    def __str__(self):
        return f'{self.openid.nickname}点赞了{self.recommend_id.recommend_id}'


class Collect(models.Model):
    id = models.BigAutoField(primary_key=True, verbose_name='收藏记录ID')
    openid = models.ForeignKey('user.User', on_delete=models.CASCADE, db_column='openid', verbose_name='收藏用户')
    stall_id = models.ForeignKey('stall.Stall', on_delete=models.CASCADE, db_column='stall_id', verbose_name='关联档口')
    collect_time = models.DateTimeField(auto_now_add=True, verbose_name='收藏时间')

    class Meta:
        db_table = 'collect'
        verbose_name = '收藏'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['openid', 'stall_id']),
            models.Index(fields=['collect_time']),
        ]
        unique_together = [['openid', 'stall_id']]

    def __str__(self):
        return f'{self.openid.nickname}收藏了{self.stall_id.stall_name}'


class Checkin(models.Model):
    checkin_id = models.CharField(max_length=12, primary_key=True, verbose_name='打卡记录ID')
    openid = models.ForeignKey('user.User', on_delete=models.CASCADE, db_column='openid', verbose_name='打卡用户')
    stall_id = models.ForeignKey('stall.Stall', on_delete=models.CASCADE, db_column='stall_id', verbose_name='关联档口')
    rating = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        validators=[MinValueValidator(1.0), MaxValueValidator(5.0)],
        verbose_name='评分'
    )
    comment = models.CharField(max_length=100, blank=True, verbose_name='简短评价')
    checkin_time = models.DateTimeField(auto_now_add=True, verbose_name='打卡时间')

    class Meta:
        db_table = 'checkin'
        verbose_name = '打卡记录'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['openid']),
            models.Index(fields=['stall_id']),
            models.Index(fields=['checkin_time']),
            models.Index(fields=['rating']),
        ]

    def __str__(self):
        return f'{self.openid.nickname}在{self.stall_id.stall_name}打卡'

    def save(self, *args, **kwargs):
        if not self.checkin_id:
            self.checkin_id = generate_id('chk')
        super().save(*args, **kwargs)

        # 更新档口的好评率
        self.stall_id.update_praise_rate()


class Comment(models.Model):
    comment_id = models.CharField(max_length=12, primary_key=True, verbose_name='评论ID')
    openid = models.ForeignKey('user.User', on_delete=models.CASCADE, db_column='openid', verbose_name='评论用户')
    recommend_id = models.ForeignKey(Recommend, on_delete=models.CASCADE, db_column='recommend_id',
                                     verbose_name='关联推荐')
    content = models.CharField(max_length=200, verbose_name='评论内容')
    reply_to = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, verbose_name='回复的评论ID')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    is_deleted = models.SmallIntegerField(default=0, choices=((1, '是'), (0, '否')), verbose_name='是否删除')

    class Meta:
        db_table = 'comment'
        verbose_name = '评论'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['openid']),
            models.Index(fields=['recommend_id']),
            models.Index(fields=['reply_to']),
            models.Index(fields=['create_time']),
            models.Index(fields=['is_deleted']),
        ]

    def __str__(self):
        return f'{self.openid.nickname}的评论({self.comment_id})'

    def save(self, *args, **kwargs):
        if not self.comment_id:
            self.comment_id = generate_id('com')
        super().save(*args, **kwargs)

        # 更新推荐内容的评论数
        if not self.is_deleted:
            self.recommend_id.increment_comment_count()