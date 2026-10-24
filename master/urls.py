from django.urls import path
from . import views

urlpatterns = [
    path('business-types/', views.BusinessTypeListView.as_view(), name='api-business-types'),
    path('business-categories/', views.BusinessCategoryListView.as_view(), name='api-business-categories'),
    path('category/', views.TemplateCategoryListView.as_view(), name='api-category'),
    path('categories/', views.TemplateCategoryListView.as_view(), name='api-categories'),
    path('subcategory/', views.TemplateSubcategoryListView.as_view(), name='api-subcategory'),
    path('subcategories/', views.TemplateSubcategoryListView.as_view(), name='api-subcategories'),
    path('subcategory/<int:category_id>/', views.TemplateSubcategoryListView.as_view(), name='api-subcategory-filtered'),
    path('subcategories/<int:category_id>/', views.TemplateSubcategoryListView.as_view(), name='api-subcategories-filtered'),
    path('templates/', views.TemplateListView.as_view(), name='api-templates'),
    path('templates/<int:category_id>/', views.TemplateListView.as_view(), name='api-templates-filtered'),
    path('trending-templates/', views.TrendingTemplateListView.as_view(), name='api-trending-templates'),
    path('flex-designs/', views.FlexDesignListView.as_view(), name='api-flex-designs'),
    path('feedback/', views.FeedbackCreateAPIView.as_view(), name='api-feedback-create'),
    path('subscription-plans/', views.SubscriptionPlanListView.as_view(), name='api-subscription-plans'),
]
