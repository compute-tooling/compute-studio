FROM webbase
ARG NEW_RELIC_TOKEN
RUN newrelic-admin generate-config $NEW_RELIC_TOKEN newrelic.ini
ENV NEW_RELIC_CONFIG_FILE=newrelic.ini

CMD newrelic-admin run-program gunicorn --bind 0.0.0.0:$PORT webapp.wsgi
