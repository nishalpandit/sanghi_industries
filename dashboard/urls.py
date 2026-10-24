from core import settings
from django.urls import path
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('users/', views.users, name='users'),
    path('brand-kits/', views.brand_kits, name='brand_kits'),
    path('templates/', views.templates, name='templates'),
    path('templates/<int:category_id>/', views.category_templates, name='category_templates'),
    path('trending-templates/', views.trending_templates, name='trending_templates'),
    path('flex-designs/', views.flex_designs, name='flex_designs'),
    path('analytics/', views.analytics, name='analytics'),
    path('subscriptions/', views.subscriptions, name='subscriptions'),
    path('reports/', views.reports, name='reports'),
    path('notifications/', views.notifications, name='notifications'),
    path('master-business/', views.master_business, name='masterBusiness'),
    path('master-category/', views.master_category, name='masterCategory'),
    path('master-city/', views.master_city, name='masterCity'),
    path('master-template-category/', views.master_template_category, name='masterTemplateCategory'),
    path('master-template-category/<int:category_id>/', views.master_template_category_detail, name='masterTemplateCategoryDetail'),
    path('master-template-subcategory/', views.master_template_subcategory, name='masterTemplateSubcategory'),
    path('feedback/', views.feedback_page, name='feedback'),
    path('ai-generated/', views.ai_generated_users, name='ai_generated_users'),
    path('ai-generated/<int:profile_id>/', views.ai_generated_user_posters, name='ai_generated_user_posters'),
    path('payments/', views.payments_list, name='payments'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)