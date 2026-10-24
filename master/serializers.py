from rest_framework import serializers
from .models import BusinessType, BusinessCategory, TemplateCategory, Template, TrendingTemplate, FlexDesign, Feedback, City


class BusinessTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessType
        fields = ['id', 'name']


class BusinessCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessCategory
        fields = ['id', 'name']


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ['id', 'name', 'state']


class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = ['id', 'name', 'category', 'description', 'file', 'status', 'usage_count']


class TemplateCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateCategory
        fields = ['id', 'name', 'image', 'parent_category']


class TemplateSubcategorySerializer(serializers.ModelSerializer):
    templates = serializers.SerializerMethodField()
    
    class Meta:
        model = TemplateCategory
        fields = ['id', 'name', 'image', 'parent_category', 'templates']
        
    def get_templates(self, obj):
        # Only return published templates in the API
        published_templates = obj.templates.filter(status='published')
        return TemplateSerializer(published_templates, many=True, context=self.context).data


class TrendingTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrendingTemplate
        fields = ['id', 'name', 'image', 'created_at']


class FlexDesignSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlexDesign
        fields = ['id', 'name', 'image', 'created_at']


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['id', 'user', 'rating', 'category', 'description', 'created_at']
        read_only_fields = ['user']

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import SubscriptionPlan
        model = SubscriptionPlan
        fields = ['id', 'name', 'features', 'price', 'duration_days', 'credits']
