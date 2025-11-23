from django.db.models import Q, Count, Min, Max
from django.core.cache import cache
from .models import Dish


class DishService:
    """菜品服务类"""

    @staticmethod
    def search_dishes(query, filters=None):
        """
        搜索菜品
        """
        if filters is None:
            filters = {}

        queryset = Dish.objects.filter(is_sold_out=0).select_related(
            'stall_id', 'stall_id__canteen_id'
        )

        # 关键词搜索
        if query:
            queryset = queryset.filter(
                Q(dish_name__icontains=query) |
                Q(taste_tag__icontains=query) |
                Q(ingredient__icontains=query) |
                Q(stall_id__stall_name__icontains=query) |
                Q(stall_id__canteen_id__canteen_name__icontains=query)
            )

        # 食堂筛选
        if filters.get('canteen_id'):
            queryset = queryset.filter(stall_id__canteen_id=filters['canteen_id'])

        # 档口筛选
        if filters.get('stall_id'):
            queryset = queryset.filter(stall_id=filters['stall_id'])

        # 菜品类型筛选
        if filters.get('dish_type'):
            queryset = queryset.filter(dish_type=filters['dish_type'])

        # 口味筛选
        if filters.get('taste'):
            queryset = queryset.filter(taste_tag__contains=[filters['taste']])

        # 价格筛选
        min_price = filters.get('min_price')
        max_price = filters.get('max_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        # 是否招牌菜筛选
        is_special = filters.get('is_special')
        if is_special is not None:
            queryset = queryset.filter(is_special=1 if is_special == 'true' else 0)

        # 排序
        sort_by = filters.get('sort_by', 'default')
        if sort_by == 'price_asc':
            queryset = queryset.order_by('price')
        elif sort_by == 'price_desc':
            queryset = queryset.order_by('-price')
        elif sort_by == 'special':
            queryset = queryset.order_by('-is_special', 'dish_name')
        else:
            queryset = queryset.order_by('-is_special', 'dish_name')

        return queryset

    @staticmethod
    def get_dish_categories():
        """
        获取菜品分类统计
        """
        cache_key = 'dish_categories'
        categories = cache.get(cache_key)

        if categories is None:
            categories = Dish.objects.filter(
                is_sold_out=0
            ).values('dish_type').annotate(
                count=Count('dish_id')
            ).order_by('-count')

            # 缓存1小时
            cache.set(cache_key, list(categories), 3600)

        return categories

    @staticmethod
    def get_price_ranges():
        """
        获取价格区间统计
        """
        cache_key = 'dish_price_ranges'
        price_ranges = cache.get(cache_key)

        if price_ranges is None:
            price_stats = Dish.objects.filter(
                is_sold_out=0
            ).aggregate(
                min_price=Min('price'),
                max_price=Max('price')
            )

            # 生成价格区间
            min_price = float(price_stats['min_price'] or 0)
            max_price = float(price_stats['max_price'] or 50)

            price_ranges = [
                {'range': '0-10', 'min': 0, 'max': 10, 'count': Dish.objects.filter(price__lte=10).count()},
                {'range': '10-20', 'min': 10, 'max': 20,
                 'count': Dish.objects.filter(price__gt=10, price__lte=20).count()},
                {'range': '20-30', 'min': 20, 'max': 30,
                 'count': Dish.objects.filter(price__gt=20, price__lte=30).count()},
                {'range': '30+', 'min': 30, 'max': None, 'count': Dish.objects.filter(price__gt=30).count()},
            ]

            # 缓存1小时
            cache.set(cache_key, price_ranges, 3600)

        return price_ranges

    @staticmethod
    def get_similar_dishes(dish, limit=8):
        """
        获取相似菜品
        """
        cache_key = f'similar_dishes:{dish.dish_id}'
        similar_dishes = cache.get(cache_key)

        if similar_dishes is None:
            # 基于口味标签和菜品类型找相似菜品
            similar_dishes = Dish.objects.filter(
                Q(dish_type=dish.dish_type) |
                Q(taste_tag__overlap=dish.taste_tag),
                is_sold_out=0
            ).exclude(
                dish_id=dish.dish_id
            ).select_related(
                'stall_id', 'stall_id__canteen_id'
            ).order_by('-is_special')[:limit]

            # 缓存30分钟
            cache.set(cache_key, list(similar_dishes), 1800)

        return similar_dishes

    @staticmethod
    def get_recommended_dishes(user_preferences=None, limit=10):
        """
        基于用户偏好推荐菜品
        """
        if user_preferences is None:
            user_preferences = {}

        queryset = Dish.objects.filter(is_sold_out=0).select_related(
            'stall_id', 'stall_id__canteen_id'
        )

        # 基于用户口味偏好推荐
        taste_prefer = user_preferences.get('taste_prefer', {})
        if taste_prefer:
            # 这里可以实现更复杂的推荐算法
            queryset = queryset.filter(
                taste_tag__overlap=list(taste_prefer.keys())
            )

        # 基于用户食材偏好推荐（排除忌口）
        forbidden_ingredient = user_preferences.get('forbidden_ingredient', {})
        if forbidden_ingredient:
            for ingredient in forbidden_ingredient:
                queryset = queryset.exclude(ingredient__contains=[ingredient])

        # 基于目标食堂推荐
        target_canteen = user_preferences.get('target_canteen', {})
        if target_canteen:
            queryset = queryset.filter(
                stall_id__canteen_id__in=list(target_canteen.keys())
            )

        return queryset.order_by('-is_special', '?')[:limit]

    @staticmethod
    def update_dish_popularity():
        """
        更新菜品热度（定时任务）
        基于相关推荐内容数量、档口热度等计算
        """
        dishes = Dish.objects.filter(is_sold_out=0)
        for dish in dishes:
            # 这里可以实现热度计算逻辑
            # 比如基于推荐内容数量、收藏数等
            pass