# Model Environment

Compute Studio runs each project in its own [Docker][1] container. [Miniconda3][2] is used as the base image, making it easy to install any package available through the [Conda package manager][5]. An `install.sh` script is created for you by the [`csk-init`][4] command in your `cs-config` directory. Compute Studio will use this script to install your package. The installation instructions for the `matchups` project are simply a bash script:

```bash
# located at: https://github.com/hdoupe/Matchups/blob/master/cs-config/install.sh
conda install -c conda-forge pandas pyarrow bokeh "paramtools>=0.5.3" fastparquet python-snappy pip
pip install git+https://github.com/hdoupe/Matchups.git@master
```

[1]: https://www.docker.com/
[2]: https://hub.docker.com/r/continuumio/miniconda3
[3]: https://conda.io/docs/
[4]: https://github.com/compute-tooling/compute-studio-kit/#set-up-the-cs-config-directory
[5]: https://docs.conda.io/en/latest/
