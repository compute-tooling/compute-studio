FROM continuumio/miniconda3

RUN conda config --append channels conda-forge
RUN conda install "python>=3.8" pip

COPY workers/requirements.txt /home

WORKDIR /home