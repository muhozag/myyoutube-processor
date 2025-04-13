from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.contrib.auth.views import LoginView

from .forms import UserRegistrationForm, CustomAuthenticationForm


class RegisterView(CreateView):
    """
    View for user registration
    """
    form_class = UserRegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('login')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Registration successful! Please log in with your new account.")
        return response


class CustomLoginView(LoginView):
    """
    Custom login view using our styled form
    """
    form_class = CustomAuthenticationForm
    template_name = 'auth/login.html'  # Using existing template