import re
from rest_framework import serializers
from master.models import BusinessType, BusinessCategory, City
from master.serializers import BusinessTypeSerializer, BusinessCategorySerializer, CitySerializer


class AuthSerializer(serializers.Serializer):
    """
    Single auth serializer that handles both steps:
    - Step 1: mobile_number only → send OTP
    - Step 2: mobile_number + otp → verify OTP
    """
    mobile_number = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=10, required=False, allow_blank=True)

    def validate_mobile_number(self, value):
        value = value.strip()
        if not re.match(r'^[6-9]\d{9}$', value):
            raise serializers.ValidationError('Enter a valid 10-digit Indian mobile number.')
        return value

    def validate_otp(self, value):
        if value:
            value = value.strip()
            if not value.isdigit():
                raise serializers.ValidationError('OTP must contain only digits.')
        return value


class CheckUserSerializer(serializers.Serializer):
    """
    Serializer to validate mobile number for checking user existence.
    """
    mobile_number = serializers.CharField(max_length=15)

    def validate_mobile_number(self, value):
        value = value.strip()
        if not re.match(r'^[6-9]\d{9}$', value):
            raise serializers.ValidationError('Enter a valid 10-digit Indian mobile number.')
        return value


class RegisterProfileSerializer(serializers.Serializer):
    registration_token = serializers.UUIDField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    date_of_birth = serializers.DateField()
    business_name = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    business_type_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text='List of BusinessType IDs (multi-select).',
    )
    business_category_id = serializers.IntegerField(
        help_text='Single BusinessCategory ID.',
    )

    def to_internal_value(self, data):
        # Handle form-data: getlist for repeated keys
        if hasattr(data, 'getlist'):
            mutable = data.copy()
            ids = data.getlist('business_type_ids')
            if ids:
                mutable.setlist('business_type_ids', [int(i) for i in ids])
            data = mutable
        return super().to_internal_value(data)

    def validate_email(self, value):
        from django.contrib.auth.models import User
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value.lower()

    def validate_business_type_ids(self, value):
        existing = set(BusinessType.objects.filter(id__in=value, is_active=True).values_list('id', flat=True))
        invalid = set(value) - existing
        if invalid:
            raise serializers.ValidationError(f'Invalid or inactive business type IDs: {list(invalid)}')
        return value

    def validate_business_category_id(self, value):
        if not BusinessCategory.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError('Invalid or inactive business category ID.')
        return value


class UserProfileResponseSerializer(serializers.Serializer):
    """Serializer for formatting the user profile in API responses."""
    id = serializers.IntegerField()
    mobile_number = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    date_of_birth = serializers.DateField(allow_null=True)
    business_name = serializers.CharField()
    profile_picture = serializers.SerializerMethodField()
    city = CitySerializer(allow_null=True)
    business_types = BusinessTypeSerializer(many=True)
    business_category = BusinessCategorySerializer(allow_null=True)
    
    # Mocking counts for now
    designs_count = serializers.SerializerMethodField()
    templates_count = serializers.SerializerMethodField()
    downloads_count = serializers.SerializerMethodField()

    def get_profile_picture(self, obj):
        # obj is the User instance (or Profile instance if updated)
        # We assume obj is User, but let's handle if obj is Profile
        profile = getattr(obj, 'profile', obj) if hasattr(obj, 'profile') else obj
        if hasattr(profile, 'profile_picture') and profile.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(profile.profile_picture.url)
            return profile.profile_picture.url
        return None

    def get_designs_count(self, obj):
        return 0

    def get_templates_count(self, obj):
        return 0
        
    def get_downloads_count(self, obj):
        return 0


class UserProfileUpdateSerializer(serializers.Serializer):
    """Serializer for updating user profile."""
    first_name = serializers.CharField(max_length=150, required=False)
    email = serializers.EmailField(required=False)
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    business_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_email(self, value):
        from django.contrib.auth.models import User
        user = self.context['request'].user
        if User.objects.filter(email__iexact=value).exclude(id=user.id).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value.lower()

    def validate_city_id(self, value):
        if value is not None and not City.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError('Invalid or inactive city ID.')
        return value


class BrandKitSerializer(serializers.ModelSerializer):
    """Serializer for the BrandKit model."""
    class Meta:
        from .models import BrandKit
        model = BrandKit
        fields = ['id', 'name', 'logo', 'brand_colors', 'phone_number', 'website', 'email', 'address']
        read_only_fields = ['id']

    def to_internal_value(self, data):
        # Handle form-data for brand_colors
        if hasattr(data, 'getlist'):
            mutable = data.copy()
            colors = data.getlist('brand_colors')
            if colors:
                # If the client sends `brand_colors` as a single JSON string like '["#ff0000", "#00ff00"]'
                if len(colors) == 1 and colors[0].startswith('[') and colors[0].endswith(']'):
                    # It is already a valid JSON string, leave it alone.
                    pass
                else:
                    # Or if it's sent as multiple form fields `brand_colors`, turn it into a JSON string
                    import json
                    mutable['brand_colors'] = json.dumps(colors)
            data = mutable
        return super().to_internal_value(data)


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for the Subscription model."""
    days_left = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()

    class Meta:
        from .models import Subscription
        model = Subscription
        fields = ['plan_name', 'end_date', 'credits_available', 'is_active', 'days_left', 'is_expired']
        read_only_fields = ['plan_name', 'end_date', 'credits_available', 'is_active']


class GeneratedPosterSerializer(serializers.ModelSerializer):
    """Serializer for the GeneratedPoster model."""
    class Meta:
        from .models import GeneratedPoster
        model = GeneratedPoster
        fields = ['id', 'image', 'created_at']
        read_only_fields = ['id']
