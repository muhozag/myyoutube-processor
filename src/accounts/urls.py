from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('logout/', views.custom_logout, name='custom_logout'),
    # We're already using Django's built-in auth views for login/logout in the main urls.py
]