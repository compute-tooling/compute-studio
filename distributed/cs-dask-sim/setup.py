import setuptools
import os

setuptools.setup(
    name="cs-dask-sim",
    description="Local package for sending a dask function over the wire.",
    url="https://github.com/compute-tooling/compute-studio",
    packages=setuptools.find_packages(),
    include_package_data=True,
)
