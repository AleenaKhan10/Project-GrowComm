"""
URL configuration for growcommunity project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts.views import home_view

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Home
    path('', home_view, name='home'),
    
    # Authentication
    path('auth/', include('accounts.urls')),
    
    # Core features
    path('community/', include('communities.urls')),
    path('profiles/', include('profiles.urls')),
    path('messages/', include('messaging.urls')),
    path('invites/', include('invites.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
