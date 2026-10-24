from django.urls import path
from . import views

app_name = 'user_dashboard'

urlpatterns = [
    path('', views.trending, name='trending'),
    path('flex-designs/', views.flex_designs_view, name='flex_designs'),
    path('my-designs/', views.my_designs, name='my_designs'),
    path('my-designs/delete/<int:design_id>/', views.design_delete, name='design_delete'),
    path('my-designs/download/<int:design_id>/', views.design_download, name='design_download'),
    path('ai-generation/', views.ai_generation, name='ai_generation'),
    path('ai-generation/generate/', views.ai_generate, name='ai_generate'),
    path('ai-generation/save/', views.design_save_ai, name='design_save_ai'),
    path('categories/', views.categories, name='categories'),
    path('feedback/', views.feedback, name='feedback'),
    path('profile/', views.profile, name='profile'),
    path('profile/manage-subscription/', views.manage_subscription, name='manage_subscription'),
    path('profile/manage-subscription/select/<int:plan_id>/', views.select_subscription_plan, name='select_subscription_plan'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
]
