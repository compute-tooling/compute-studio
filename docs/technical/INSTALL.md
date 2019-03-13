# Installation

COMP is powered by a Django application and a Flask/Celery/Redis worker cluster. The Django application is what powers the site at compmodels.com and what submits jobs to the worker cluster. The worker cluster is where the models are run. These components are started by two docker compose commands.

**Docker**
1. Install the stable community edition of Docker. Install the version that
corresponds to your operating system from this [page](https://docs.docker.com/install/).
Make sure the docker app is running. You should see a whale icon in your
toolbar. If you are not on a Mac, see the [docker-compose installation page](https://docs.docker.com/compose/install/)
for information on how to set this up on your operating system.

2. Build the local docker images or pull them from docker hub.
    - From the comp top-level directory, run `docker-compose up` to start the django component.
    - Go to the `distributed` directory and run `docker-compose up` to start the worker cluster.

    COMP should be running locally at this point. If these steps do not work for you, then you can open up an [issue](https://github.com/comp-org/comp/issues) to get assistance.

**Run tests on the django component**

This command should be run from the top-level `comp` directory. The tests depend on the worker cluster. Thus, the worker cluster should be running in the background or in another window before running the command below.

    ```
    docker-compose run web py.test webapp/apps -v
    ```

**Run tests on the worker components**

This command should be run from the `distributed` directory.

- Flask:
    ```
    docker-compose run flask py.test -v
    ```
- Tests for other components coming soon...
