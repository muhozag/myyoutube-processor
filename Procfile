# Procfile for local deployment
web: cd src && python manage.py migrate && python manage.py ensure_superuser && python manage.py collectstatic --noinput && gunicorn myyoutubeprocessor.wsgi:application --log-file -
worker: cd src && celery -A myyoutubeprocessor worker --loglevel=info