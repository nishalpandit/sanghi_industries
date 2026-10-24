from rest_framework.generics import ListAPIView, CreateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import BusinessType, BusinessCategory
from .serializers import BusinessTypeSerializer, BusinessCategorySerializer


class BusinessTypeListView(ListAPIView):
    serializer_class = BusinessTypeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BusinessType.objects.filter(is_active=True)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return self._wrap(response)

    def _wrap(self, response):
        from rest_framework.response import Response
        return Response({
            'success': True,
            'data': response.data,
        })


class BusinessCategoryListView(ListAPIView):
    serializer_class = BusinessCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BusinessCategory.objects.filter(is_active=True)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return self._wrap(response)

    def _wrap(self, response):
        from rest_framework.response import Response
        return Response({
            'success': True,
            'data': response.data,
        })


class TemplateCategoryListView(ListAPIView):
    from .models import TemplateCategory
    from .serializers import TemplateCategorySerializer
    
    serializer_class = TemplateCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from .models import TemplateCategory
        # Only top-level categories
        return TemplateCategory.objects.filter(is_active=True, parent_category__isnull=True).prefetch_related('templates')

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return self._wrap(response)

    def _wrap(self, response):
        from rest_framework.response import Response
        return Response({
            'success': True,
            'data': response.data,
        })


class TemplateSubcategoryListView(ListAPIView):
    from .models import TemplateCategory
    from .serializers import TemplateSubcategorySerializer
    
    serializer_class = TemplateSubcategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from .models import TemplateCategory
        # Only subcategories (parent_category is not null)
        queryset = TemplateCategory.objects.filter(is_active=True, parent_category__isnull=False).prefetch_related('templates')
        
        # Filter by specific parent category from URL kwargs, query params, or POST form-data
        parent_id = self.kwargs.get('category_id')
        if not parent_id:
            for key in ['category_id', 'catagory_id', 'parent_id', 'parent_category_id']:
                parent_id = self.request.query_params.get(key)
                if parent_id:
                    break
        if not parent_id and hasattr(self.request, 'data') and self.request.data:
            for key in ['category_id', 'catagory_id', 'parent_id', 'parent_category_id']:
                parent_id = self.request.data.get(key)
                if parent_id:
                    break
            
        if parent_id:
            queryset = queryset.filter(parent_category_id=parent_id)
            
        return queryset

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return self._wrap(response)
        
    def post(self, request, *args, **kwargs):
        # Allow POST requests so the client can send form-data
        return self.list(request, *args, **kwargs)

    def _wrap(self, response):
        from rest_framework.response import Response
        return Response({
            'success': True,
            'data': response.data,
        })


class TemplateListView(ListAPIView):
    from .models import Template
    from .serializers import TemplateSerializer
    
    serializer_class = TemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from .models import Template
        # Only published templates
        queryset = Template.objects.filter(status='published')
        
        # Filter by specific category/subcategory from URL kwargs, query params, or POST form-data
        cat_id = self.kwargs.get('category_id')
        if not cat_id:
            for key in ['category_id', 'catagory_id', 'subcategory_id', 'subcatagory_id', 'category', 'subcategory']:
                cat_id = self.request.query_params.get(key)
                if cat_id:
                    break
        if not cat_id and hasattr(self.request, 'data') and self.request.data:
            for key in ['category_id', 'catagory_id', 'subcategory_id', 'subcatagory_id', 'category', 'subcategory']:
                cat_id = self.request.data.get(key)
                if cat_id:
                    break
            
        if cat_id:
            queryset = queryset.filter(category_id=cat_id)
            
        return queryset

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return self._wrap(response)
        
    def post(self, request, *args, **kwargs):
        # Allow POST requests so the client can send form-data
        return self.list(request, *args, **kwargs)

    def _wrap(self, response):
        from rest_framework.response import Response
        return Response({
            'success': True,
            'data': response.data,
        })


class TrendingTemplateListView(ListAPIView):
    from .models import TrendingTemplate
    from .serializers import TrendingTemplateSerializer
    
    serializer_class = TrendingTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from .models import TrendingTemplate
        return TrendingTemplate.objects.all()

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return self._wrap(response)

    def _wrap(self, response):
        from rest_framework.response import Response
        return Response({
            'success': True,
            'data': response.data,
        })


class FlexDesignListView(ListAPIView):
    from .models import FlexDesign
    from .serializers import FlexDesignSerializer
    
    serializer_class = FlexDesignSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from .models import FlexDesign
        return FlexDesign.objects.all()

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return self._wrap(response)

    def _wrap(self, response):
        from rest_framework.response import Response
        return Response({
            'success': True,
            'data': response.data,
        })


class FeedbackCreateAPIView(CreateAPIView):
    from .serializers import FeedbackSerializer
    
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # Save the feedback with the logged-in user
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        from rest_framework.response import Response
        return Response({
            'success': True,
            'message': 'Feedback submitted successfully',
            'data': response.data,
        })

class SubscriptionPlanListView(ListAPIView):
    from .models import SubscriptionPlan
    from .serializers import SubscriptionPlanSerializer
    queryset = SubscriptionPlan.objects.filter(is_active=True).order_by('price')
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [AllowAny]
