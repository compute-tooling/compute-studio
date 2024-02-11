import setuptools
import os

if os.path.exists("README.md"):
    with open("README.md", "r") as f:
        long_description = f.read()
else:
    long_description = ""


setuptools.setup(
    name="cs-workers",
    version=os.environ.get("TAG", "0.0.0"),
    author="Hank Doupe",
    author_email="hank@compute.studio",
    description=("Build, publish, and run Compute Studio workers."),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/compute-tooling/compute-studio",
    packages=setuptools.find_packages(),
    install_requires=[
        "redis",
        "kubernetes",
        "gitpython",
        "pyyaml",
        "google-cloud-secret-manager",
        "httpx",
        "tornado",
        "cs-storage>=1.11.0",
        "docker",
        "pydantic[email,dotenv]",
        "pydantic-settings",
        "fastapi",
        "rq",
        "alembic",
    ],
    include_package_data=True,
    entry_points={
        "console_scripts": ["cs-workers=cs_workers.cli:cli", "csw=cs_workers.cli:cli"]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Operating System :: OS Independent",
    ],
)
