# COMP

**COMP** is an open-source platform for sharing computational models. 

To see COMP in action, visit [compmodels.com](www.compmodels.com).

- Developers and organizations  share their models with the public without paying for the public's compute. 
- Users pay for compute when submitting each simulation.  
- Organizations share models internally, for a per-user fee. 

## Contributing

COMP is an open source project and anyone can contribute code or suggestions. 

You can reach COMP developers to discuss how to get started by opening an issue or joining the COMP Community [chat room](https://matrix.to/#/!WQWxPnwidsSToqkeLk:matrix.org).  

## License

COMP is licensed under the open source [GNU Affero General Public License](/License.txt) to Henry Doupe, to be transferred to COMP Industries, LLC.

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

**Set stripe and email keys**
TODO: app should run without these.
```
./secret.sh
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
py.test webapp/apps -v
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
