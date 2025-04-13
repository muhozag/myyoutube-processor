"""
URL configuration for myyoutubeprocessor project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from django.contrib import admin
from accounts.views import custom_logout

# Import the custom admin site instance directly
from .admin import custom_admin_site

# Use the existing instance instead of creating a new one
admin.site = custom_admin_site
admin.sites.site = admin.site

urlpatterns = [
    path('admin/', admin.site.urls),
    path('videos/', include('videos.urls')),
    path('', RedirectView.as_view(pattern_name='video_list', permanent=False)),
    
    # Authentication URLs
    path('accounts/login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('accounts/logout/', custom_logout, name='logout'),
    path('accounts/password_change/', auth_views.PasswordChangeView.as_view(template_name='auth/password_change.html', 
                                                                         success_url='/accounts/password_change/done/'), 
         name='password_change'),
    path('accounts/password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='auth/password_change_done.html'), 
         name='password_change_done'),
    
    # Accounts app URLs
    path('accounts/', include('accounts.urls')),
]
