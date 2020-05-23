FROM continuumio/miniconda3

USER root
RUN  apt-get update && apt install libgl1-mesa-glx --yes

RUN conda update conda
RUN conda config --append channels conda-forge
RUN conda install "python>=3.8" pip

COPY requirements.txt /home

WORKDIR /home