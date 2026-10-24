from django.urls import path
from . import views

urlpatterns = [
    path('check-user/', views.CheckUserView.as_view(), name='api-check-user'),
    path('check-subscription/', views.CheckSubscriptionView.as_view(), name='api-check-subscription'),
    path('auth/', views.AuthView.as_view(), name='api-auth'),
    path('register/', views.RegisterProfileView.as_view(), name='api-register'),
    path('profile/', views.ProfileView.as_view(), name='api-profile'),
    path('brand-kits/', views.BrandKitView.as_view(), name='api-brand-kits'),
    path('brand-kits/<int:pk>/', views.BrandKitDetailView.as_view(), name='api-brand-kit-detail'),
    path('subscription/', views.SubscriptionView.as_view(), name='api-subscription'),
    path('generated-posters/', views.GeneratedPosterCreateView.as_view(), name='api-generated-posters-create'),
    path('generated-posters/list/', views.GeneratedPosterListView.as_view(), name='api-generated-posters-list'),
    path('payment/', views.PaymentAPIView.as_view(), name='api-payment'),
]
