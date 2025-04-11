web: cd src && gunicorn myyoutubeprocessor.wsgi:application --log-file -
worker: cd src && celery -A myyoutubeprocessor worker --loglevel=info