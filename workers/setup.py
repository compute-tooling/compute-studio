import setuptools
import os

if os.path.exists("README.md"):
    with open("README.md", "r") as f:
        long_description = f.read()
else:
    long_description = ""


setuptools.setup(
    name="cs-publish",
    version=os.environ.get("TAG", "0.0.0"),
    author="Hank Doupe",
    author_email="hank@compute.studio",
    description=("Build, publish, and run Compute Studio workers."),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/compute-tooling/compute-studio-workers",
    packages=setuptools.find_packages(),
    install_requires=["celery", "redis", "gitpython", "pyyaml"],
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "cs-publish=cs_publish.client.publish:main",
            "cs-secrets=cs_publish.client.secrets:main",
            "cs-job=cs_publish.executors.kubernetes:main",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Operating System :: OS Independent",
    ],
)
