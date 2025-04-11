web: cd src && gunicorn myyoutubeprocessor.wsgi --log-file -
worker: cd src && celery -A myyoutubeprocessor worker --loglevel=info