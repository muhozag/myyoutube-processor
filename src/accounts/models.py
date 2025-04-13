from django.db import models
from django.contrib.auth.models import User

# We'll use the built-in Django User model
# This file is primarily a placeholder for future customizations
"""
If you need to extend the User model in the future, consider using:

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    # Add custom fields here
"""