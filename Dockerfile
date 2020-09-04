FROM webbase

RUN pip install --upgrade sentry-sdk

CMD gunicorn --bind 0.0.0.0:$PORT webapp.wsgi
