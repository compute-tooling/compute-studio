FROM heroku/miniconda:3

# Grab requirements.txt.
ADD ./requirements.txt /requirements.txt
ADD ./conda-requirements.txt /conda-requirements.txt

# Install dependencies
RUN conda update conda
RUN conda install -c anaconda --file conda-requirements.txt --yes
RUN pip install -r requirements.txt

# Add our code
ADD ./webapp /opt/webapp/
WORKDIR /opt

ADD ./templates /opt/templates/

ADD ./manage.py /opt/
ADD ./static /opt/static/
RUN python manage.py collectstatic --noinput

CMD gunicorn --bind 0.0.0.0:$PORT webapp.wsgi
