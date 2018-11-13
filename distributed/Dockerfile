FROM continuumio/miniconda3

USER root
RUN  apt-get update && apt install libgl1-mesa-glx --yes

RUN mkdir /home/distributed
RUN mkdir /home/distributed/api
COPY requirements.txt home/distributed

WORKDIR /home/distributed/api

RUN conda config --append channels conda-forge

WORKDIR /home/distributed

RUN conda install python=3.6 numpy>=1.12.1 pandas>=0.23.0 \
    matplotlib numba six bokeh>=0.12.7 mock xlrd \
    sphinx nomkl

RUN pip install -r requirements.txt

WORKDIR /home/distributed/api
