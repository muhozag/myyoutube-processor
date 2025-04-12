import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Creates a superuser if none exists or resets admin password on Railway'

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
        
        # Check if we're on Railway
        on_railway = bool(os.environ.get('RAILWAY_STATIC_URL') or os.environ.get('RAILWAY_SERVICE_NAME'))
        
        # Get password from environment or use a default for Railway
        if on_railway:
            password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin')
        else:
            password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
        
        if User.objects.filter(is_superuser=True).count() == 0:
            # Create a new superuser if none exists
            if not password:
                self.stdout.write(self.style.WARNING('Superuser not created because DJANGO_SUPERUSER_PASSWORD environment variable is not set'))
                return
                
            User.objects.create_superuser(username, email, password)
            self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" created successfully!'))
        elif on_railway:
            # On Railway, also update the admin password to ensure it's accessible
            try:
                admin_user = User.objects.get(username=username)
                admin_user.set_password(password)
                admin_user.save()
                self.stdout.write(self.style.SUCCESS(f'Updated password for existing admin user "{username}" on Railway'))
            except User.DoesNotExist:
                # If the username from env var doesn't exist but other superusers do, create this one anyway
                User.objects.create_superuser(username, email, password)
                self.stdout.write(self.style.SUCCESS(f'Created additional superuser "{username}" on Railway'))
        else:
            self.stdout.write(self.style.SUCCESS('Superuser already exists. No action taken.'))