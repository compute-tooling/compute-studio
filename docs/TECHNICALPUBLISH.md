Components
-----------------

COMP has three essential components:

- **Webapp**

  The webapp is a Django application, and it is the workhorse of COMP. It validates and formats the inputs for each modeling project. It determines whether the data is submitted for a model run with its own validation methods and by running it through the modeling project's validation methods. If the inputs data is not valid, then the warnings and errors will be shown to the user. If the inputs data is valid, then it will be submitted to the model through the distributed API.

  The goal of the `core` app is to provide a framework that can be used with varying levels of customization. The `core` app by itself provides enough functionality to publish the average model on COMP. However, more customized approaches will be added to the `contrib` app. The first example is the `taxcalcstyle` package. This approach is specific for the [Tax-Calculator][3] style of inputs, naming convention, JSON files, and error messages. Other approaches are welcome, too. However, COMP recommends giving the `core` app a try before checking out the custom approaches or building your own.

  The Django webapp also handles login and user capabilities.

- **Templates and Frontend scripts**

  This determines how the data is displayed to the user. It is a mix of HTML, CSS, JavaScript, and Django templating language. The relevant parts of this component are the inputs form, the field HTML files that wrap the modeling parameters, and the outputs page which displays the results data and fascillitates downloading the results.

- **Distributed API**

  This is where the data is submitted to the modeling project. It is a lightweight REST API that wraps the interaction between the webapp and the Celery workers. It is composed of a single Flask app, a group of one or more Celery workers for each modeling project, and a Redis instance that serves as a broker for Celery. In the near future, all interactions between COMP and the upstream projects will occur over the Distributed API. This means that each project gets to specify its own environment and will not need to compromise on environment requirements with other modeling projects.


How to publish a model on COMP
-------------------------------

Working through the installation instructions in the COMP `README.md` document is strongly recommended. This will give a more intuitive feel for how this project is setup. In addition, it will be easier to resolve any issues relating to the installation of the webapp before any changes are made to it. There is also an example app, `compbaseball` ([github repo][4]). This may help if there are some questions about which parts need to be filled in or what structure the data should have.

1. Use the app templating script to automatically write most of the boiler plate code required to put the project on COMP.
    ```
    python app_template/template.py "project_name" "Project Title"
    ```

    where `"project_name"` is the name that will be used throughout the codebase to describe the COMP classes and functions pertaining to this app and `"Project Title"` is the name that will be displayed to the user and will be used to look up the project in the `Project` table. This command will write a new app in `webapp/apps/projects/{project_name}`, a new module in the `distributed/api/celery_app/{project_name}_tasks.py`, and a new `Dockerfile` at `distributed/dockerfiles/projects/Dockerfile.{project_name}`.

2. Add an entry into the `webapp/apps/billing.json` file:

    ```
        "project_name": {
            "name": "Project-Title",
            "amount": 0,
            "metered_amount": 1,
            "currency": "usd",
            "interval": "month",
            "trial_days": 0,
            "server_cost": 0.10,
            "exp_task_time": 200,
            "exp_num_tasks": 1,
            "is_public": true
        }
    ```

    The only attributes that should be edited are:
      - name - The title of the webapp (same as the project-title used with the template module)
      - server_cost - The price of the AWS server in dollars per hour. A good resource to figure out which AWS server is needed for this model is the [AWS EC2 pricing page][2].
      - exp_task_time - On average, how long in seconds will each task take? This should be estimated carefully since a time limit will be applied to each task in the celery app. When the task goes over the allotted time, it will be killed.
      - exp_num_tasks - On average, how many tasks will be run?
      - is_public - Toggles whether a project is viewable by all COMP users or just a verified subset of them. This feature has not yet been implemented.

3. Append the new app to `INSTALLED_APPS` in the Django `settings.py` module:

    ```
    'webapp.apps.projects.{project_name}'
    ```

4. Append the app's URLs to the `webapp/urls.py` module:

    ```
    path('{project_name}/', include('webapp.apps.projects.project_name.urls')),
    ```

5. Make and run migrations via the following commands:
    - `python manage.py makemigrations`
    - `python manage.py runserver`

6. (Temporary) Add package to `conda-requirements.txt` or `requirements.txt`. Use `conda-requirements.txt` if the project relies on the numpy/scipy/pandas stack of scientific computing Python packages.

6. Fill in the API endpoints as described in the API endpoints section. The locations to be filled in are:
    - `webapp.apps.projects.{project_name}.displayer.Display.package_defaults`
    - `webapp.apps.projects.{project_name}.parser.Parser.parse_parameters`
    - `api.celery_app.{project_name}_tasks.{project_name}_tasks.{project_name}_task`
    - `api.celery_app.{project_name}_tasks.{project_name}_tasks.{project_name}_postprocess`

7. Create a task route for the new celery worker in `celery_app.__init__.py`:

    ```
    '{project_name}_tasks.*': {'queue': '{project_name}_queue'},
    ```

8. Import the new Celery tasks and add a new endpoint in `api/endpoints.py`, following the templates:

    Import Celery tasks:
    ```
    from api.celery_app.{project_name}_tasks import (
        {project_name}_postprocess,
        {project_name}_task)
    ```

    API route:
    ```
    @bp.route("/{project_name}", methods=['POST'])
    def {project_name}_endpoint():
        return aggr_endpoint({project_name}_task, {project_name}_postprocess)
    ```

9. Fill out the `tags` and `aggr_tags` attributes on the webapp.apps.projects.{project_name}.views Outputs View.

10. (Temporary) Add project to the dropdown menu in `templates/base.html`:

    ```html
    <a class="dropdown-item" href="{% url '{project_name}' %}">{Project-Title}</a>
    ```

11. Add installation instructions to the project's `Dockerfile` at `distributed/dockerfiles/projects/Dockerfile.{project_app}_tasks`. The section where the commands need to be filled in is blocked out with a comment. For those who do not have much experience with Docker, the commands are very similar to Unix or Linux bash commands. For example,
    - Run bash commands with the `RUN` command:
        ```docker
        RUN conda install pandas
        RUN git clone https://github.com/hdoupe/compbaseball
        ```
    - Copy files to the image with the `COPY` command (note: working directory is `distributed`):
        ```docker
        COPY ./compbaseball /home/distributed/compbaseball`
        ```

    Once these instructions have been added, add the `Dockerfile` to the list of docker images to be built by following the template commands in the `Makefile`. Next, add the new worker to the `docker-compose.yml` file according to the template configuration there. Set a tag for these images like so: `export TAG=test-build`, build the images: `make dist-build`, and spin up the containers from the `distributed` directory: `cd distributed && docker-compose up`.

12. The project should be able to run locally at this point. Give it a test run by starting the Django webapp in one terminal window: `python manage.py runserver` and starting the backend API in another window: `cd distributed && docker-compose up`. Once you've created a *local* account, you will be able to run the new app.

13. Create test data by doing a model run. Ideally, this should be done in a way that creates a small but representitive dataset. Download this dataset by clicking the "Download Raw Output" option and placing it at `webapp/apps/projects/{project_name}/tests/outputs.json`. Fill in a few raw input fields in the `upstream_parameters` dictionary located in the `inputs_ok` method of the test class. The dictionary should look like this:

    ```python
    upstream_parameters = {
        # use your own parameters here
        "pitcher": "Max Scherzer",
    }
    ```

    Run the tests with py.test: `py.test webapp/apps/projects/{project_name}/tests/test_views.py -s -v`


[1]: https://github.com/hdoupe/ParamProject
[2]: https://aws.amazon.com/ec2/pricing/on-demand/
[3]: https://github.com/PSLmodels/Tax-Calculator
[4]: https://github.com/hdoupe/compbaseball