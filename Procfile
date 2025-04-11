web: cd src && python manage.py collectstatic --noinput && gunicorn myyoutubeprocessor.wsgi:application --log-file -
worker: cd src && celery -A myyoutubeprocessor worker --loglevel=info