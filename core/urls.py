from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin-dashboard/', include('dashboard.urls')),
    path('user-dashboard/', include('user_dashboard.urls')),
    path('', include('webportal.urls')),
    # REST API endpoints
    path('api/users/', include('users.urls')),
    path('api/master/', include('master.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
