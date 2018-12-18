# COMP

**COMP** is an open-source utility for sharing computational models.

To see COMP in action, visit [compmodels.com](www.compmodels.com).

Features:
- Developers share their public models for free.
- Users pay for their own compute, at cost.

Under development: 
- Developers choose to pay for their users' compute.
- Developers coose to share models privately, for a fee.
- Developers may share non-tabular output. 

Planned:
- Users may use a COMP REST API to run simulations and build GUI simulation pages.  
- Developers may charge a model subscription, for a fee.
- Users may upload and download simulation input files from the COMP GUI. 



## Contributing

COMP is an open source project and anyone can contribute code or suggestions.

You can reach COMP developers to discuss how to get started by opening an issue or joining the COMP Community [chat room](https://matrix.to/#/!WQWxPnwidsSToqkeLk:matrix.org).

## License

COMP is licensed under the open source [GNU Affero General Public License](/License.txt) to Compute Tooling, LLC.

## Install instructions

**Database**
1. For install: See DATABASE.md
2. Database is created with the following command:
```
export DATABASE_USER=YOUR_USERNAME_HERE && source ./webapp_env.sh
```
Note: your user name is your computer "username":
`USER-MacBook-Pro:COMP username$`

**Build & Activate Python Environment**

```
./python_env.sh
```

```
source activate comp-dev
```

**Set stripe and email keys, if available**
```
source secret.sh
```

**Set other environment variables, such as the backend hostname**
```
source webapp_env.sh
```

**Django setup**
```
python manage.py migrate
python manage.py collectstatic
```
**Run Django server**
```
python manage.py runserver
```

**Run tests**
```
py.test webapp/apps -v -k "not requires_stripe"
```

**Docker**
Note: this is only necessary if you want to run the backend workers. The frontend works just fine without this component.
1. Install the stable community edition of Docker. Install the version that
corresponds to your operating system from this [page](https://docs.docker.com/install/).
Make sure the docker app is running. You should see a whale icon in your
toolbar. If you are not on a Mac, see the [docker-compose installation page](https://docs.docker.com/compose/install/)
for information on how to set this up on your operating system.
2. Export the image tag that you want to use: `export TAG=dev`
Build the images: `make dist-build`
Navigate to `COMP/distributed` directory and run: `docker-compose up`
