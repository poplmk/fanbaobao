from rest_framework import serializers
from .models import Canteen


class CanteenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Canteen
        fields = [
            'canteen_id', 'canteen_name', 'canteen_icon', 'latitude', 'longitude',
            'address', 'business_hours', 'stall_count', 'is_active', 'create_time'
        ]
        read_only_fields = ['canteen_id', 'stall_count', 'create_time']


class CanteenCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Canteen
        fields = [
            'canteen_name', 'canteen_icon', 'latitude', 'longitude',
            'address', 'business_hours', 'is_active'
        ]


class CanteenListSerializer(serializers.ModelSerializer):
    distance = serializers.FloatField(required=False, read_only=True)

    class Meta:
        model = Canteen
        fields = [
            'canteen_id', 'canteen_name', 'canteen_icon', 'latitude', 'longitude',
            'address', 'business_hours', 'stall_count', 'is_active', 'distance'
        ]