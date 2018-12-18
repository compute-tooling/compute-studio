# Model Environment

COMP runs each project in its own [Docker][1] container. [Miniconda3][2] is used as the base image. This means that [`conda`][3] is installed by default. Thus, all packages available through the `conda` package manager can easily be installed. Include installation instructions in your email to me, and I will add them to the project's `Dockerfile`. If you are inclined, you will have access to this `Dockerfile` and will be able to build the Docker image and experiment with it. The installation instructions for the `compbaseball` project are simply a bash script:

```bash
conda install pandas pyarrow
pip install pybaseball compbaseball>=0.1.3
```


[1]: https://www.docker.com/
[2]: https://hub.docker.com/r/continuumio/miniconda3
[3]: https://conda.io/docs/