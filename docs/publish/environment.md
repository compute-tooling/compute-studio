# Model Environment

Compute Studio runs each project in its own [Docker][1] container. [Miniconda3][2] is used as the base image, making it easy to install any package available through the [Conda package manager][5]. An `install.sh` script is created for you by the [`csk init`][4] command. Compute Studio will use this script to install your package. The installation instructions for a [Dash app](/publish/data-viz/guide.html#dash) are simple:

```bash
# bash commands for installing your package

pip install -U dash
```

[1]: https://www.docker.com/
[2]: https://hub.docker.com/r/continuumio/miniconda3
[3]: https://conda.io/docs/
[4]: https://github.com/compute-tooling/compute-studio-kit/#set-up-the-cs-config-directory
[5]: https://docs.conda.io/en/latest/
