import os
import secrets
import string
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Creates a superuser if none exists or resets admin password'

    def generate_secure_password(self, length=16):
        """Generate a cryptographically secure password"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
        
        # Check if we're in production environment
        is_production = not os.environ.get('DEBUG', '').lower() == 'true'
        
        # Get password from environment - NEVER use a default password
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
        
        if User.objects.filter(is_superuser=True).count() == 0:
            # Create a new superuser if none exists
            if not password:
                if is_production:
                    # Generate a secure random password for production
                    password = self.generate_secure_password()
                    self.stdout.write(
                        self.style.WARNING(
                            f'Generated secure password for superuser: {password}\n'
                            'IMPORTANT: Save this password immediately! This is the only time it will be displayed.'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            'Superuser not created because DJANGO_SUPERUSER_PASSWORD environment variable is not set'
                        )
                    )
                    return
                
            User.objects.create_superuser(username, email, password)
            self.stdout.write(
                self.style.SUCCESS(f'Superuser "{username}" created successfully')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('Superuser already exists')
            )