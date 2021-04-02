# Project Environment

This guide will walk you through how to build your project's environment on Compute Studio. If you have any questions about these steps or your project requires any extra accomodation, please [send Hank an email](mailto:hank@compute.studio).

## 1. Connect your code

Enter your code repository URL and branch that you'd like to deploy.

The example below tells C/S to download the code from a Github repository named [hdoupe/cs-dash-demo](https://github.com/hdoupe/cs-dash-demo) and checkout a branch named `main`. Since this is a GitHub repository, you can set the branch name to be a non-default branch like `dev` or another release tag like `1.0.0`.

TODO add screenshot

## 2. Build your project environment using community established practices

C/S will use existing dependency files like `environment.yaml` or `requirements.txt` to install your project's dependencies.

Here's an example `requirements.txt` file for the [hdoupe/dash-demo](https://compute.studio/hdoupe/dash-demo) project:

```
# requirements.txt

dash
```

Here's an example `environment.yaml` file that's used by the [hdoupe/matchups](https://compute.studio/hdoupe/matchups) project:

```yaml
# environment.yml

name: matchups-dev
channels:
  - conda-forge
dependencies:
  - paramtools
  - "python-dateutil>=2.8.0"
  - bokeh
  - numpy
  - pandas
  - pyarrow
  - fastparquet
  - python-snappy
  - pip
  - pip:
      - cs-kit
      - "-e ." # create a local installation of matchups
```

## 3. (optional) Provide custom instructions with a `cs-config/install.sh` file

The `cs-config/install.sh` file is helpful if your project requires custom logic for setting up its environment. This file is run after C/S has checked for and processed any standard dependency files. Here are a couple situations where a `cs-config/install.sh` script may be helpful:

- Installing dependecies that are only required when running on C/S and aren't necessary for local development or usage.
- Using a package manager that C/S does not _yet_ support like `apt`, R's package manager, or Julia's package manager.

For example, [PSLmodels/Tax-Brain](https://compute.studio/PSLmodels/Tax-Brain) requires some linux packages for rendering latex and uses a `cs-config/install.sh` script like this one:

```bash
# cs-config/install.sh

apt-get install texlive-plain-generic texlive -y
```

## 4. (optional) Specify how much compute your project needs

C/S allocates up to 7 CPU's and 24 GB of memory to run your project. You can set this from the environment section under the "Advanced Configuration" heading:

TODO add image

If you need more compute resources, please [send Hank an email](mailto:hank@compute.studio) and he will work with you to accomodate your project's needs.
