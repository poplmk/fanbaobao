from rest_framework import serializers
from .models import Dish
from apps.stall.serializers import StallSimpleSerializer


class DishSerializer(serializers.ModelSerializer):
    stall_info = StallSimpleSerializer(source='stall_id', read_only=True)
    average_rating = serializers.SerializerMethodField()
    recommendations_count = serializers.SerializerMethodField()
    is_collected = serializers.SerializerMethodField()

    class Meta:
        model = Dish
        fields = [
            'dish_id', 'stall_id', 'stall_info', 'dish_name', 'dish_image', 'price',
            'dish_type', 'taste_tag', 'ingredient', 'is_special', 'is_sold_out',
            'create_time', 'update_time', 'average_rating', 'recommendations_count',
            'is_collected'
        ]
        read_only_fields = ['dish_id', 'create_time', 'update_time']

    def get_average_rating(self, obj):
        return obj.get_average_rating()

    def get_recommendations_count(self, obj):
        return obj.get_related_recommendations_count()

    def get_is_collected(self, obj):
        """获取当前用户是否收藏了该菜品所属的档口"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            from apps.recommend.models import Collect
            return Collect.objects.filter(
                openid=request.user,
                stall_id=obj.stall_id
            ).exists()
        return False


class DishCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dish
        fields = [
            'stall_id', 'dish_name', 'dish_image', 'price', 'dish_type',
            'taste_tag', 'ingredient', 'is_special', 'is_sold_out'
        ]

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError('价格必须大于0')
        return value

    def validate_taste_tag(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('口味标签必须是数组')
        return value

    def validate_ingredient(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('食材必须是数组')
        return value


class DishListSerializer(serializers.ModelSerializer):
    stall_name = serializers.CharField(source='stall_id.stall_name', read_only=True)
    canteen_name = serializers.CharField(source='stall_id.canteen_id.canteen_name', read_only=True)
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = Dish
        fields = [
            'dish_id', 'dish_name', 'dish_image', 'price', 'dish_type',
            'taste_tag', 'is_special', 'is_sold_out', 'stall_name', 'canteen_name',
            'average_rating'
        ]

    def get_average_rating(self, obj):
        return obj.get_average_rating()


class DishUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dish
        fields = [
            'dish_name', 'dish_image', 'price', 'dish_type', 'taste_tag',
            'ingredient', 'is_special', 'is_sold_out'
        ]


class DishSimpleSerializer(serializers.ModelSerializer):
    stall_name = serializers.CharField(source='stall_id.stall_name', read_only=True)

    class Meta:
        model = Dish
        fields = [
            'dish_id', 'dish_name', 'dish_image', 'price', 'is_special', 'is_sold_out',
            'stall_name'
        ]


class DishSearchSerializer(serializers.ModelSerializer):
    stall_name = serializers.CharField(source='stall_id.stall_name', read_only=True)
    canteen_name = serializers.CharField(source='stall_id.canteen_id.canteen_name', read_only=True)

    class Meta:
        model = Dish
        fields = [
            'dish_id', 'dish_name', 'dish_image', 'price', 'dish_type',
            'taste_tag', 'is_special', 'stall_name', 'canteen_name'
        ]