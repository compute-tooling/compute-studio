import setuptools
import os

if os.path.exists("README.md"):
    with open("README.md", "r") as f:
        long_description = f.read()
else:
    long_description = ""


setuptools.setup(
    name="cs-secrets",
    version=os.environ.get("TAG", "0.0.0"),
    author="Hank Doupe",
    author_email="hank@compute.studio",
    description=("Base class for managing secrets on Compute Studio."),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/compute-tooling/compute-studio",
    packages=setuptools.find_packages(),
    install_requires=["google-cloud-secret-manager",],
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Operating System :: OS Independent",
    ],
)
