FROM heroku/miniconda:3

# allow print statements
ENV PYTHONUNBUFFERED 1

# Grab requirements.txt.
RUN mkdir /code
WORKDIR /code
ADD ./requirements.txt /code/requirements.txt
ADD ./pytest.ini /code/pytest.ini

# Install dependencies
RUN conda update conda
RUN conda install -c conda-forge "python>=3.7.0" pip "paramtools>=0.5.4" bokeh --yes
RUN pip install -r requirements.txt

# Add our code
ADD ./webapp /code/webapp/
WORKDIR /code

ADD ./templates /code/templates/

ADD ./manage.py /code/
ADD ./static /code/static/
RUN python manage.py collectstatic --noinput

CMD gunicorn --bind 0.0.0.0:$PORT webapp.wsgi
