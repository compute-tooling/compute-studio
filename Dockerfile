FROM webbase

RUN pip install --upgrade sentry-sdk

CMD gunicorn --workers 3 --bind 0.0.0.0:$PORT webapp.wsgi
