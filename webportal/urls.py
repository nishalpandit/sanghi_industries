from django.urls import path
from . import views

app_name = 'webportal'

urlpatterns = [
    path('', views.index, name='index'),
]
