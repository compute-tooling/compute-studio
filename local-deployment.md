1. Create the `cs-config.yaml` file:

   ```yaml
   webapp:
    PROJECT: cs-workers-dev
    HOST: null # internal networking for now but e.g. dev.compute.studio

    dbVolume:
        volumes:
        - name: db-volume
            hostPath:
            path: /db-data
            type: Directory

   workers:
    CS_URL: "http://web"
    CLUSTER_HOST: null # internal networking for now but e.g. devcluster.compute.studio
    BUCKET: "some-bucket"
    PROJECT: "cs-workers-dev"

    redisVolume:
        volumes:
        - name: redis-volume
            hostPath:
            path: /redis-data
            type: Directory
   ```

1. Update `kind-config.yaml` with your username:

   ```bash
   sed -i '/s/hankdoupe/$USER' kind-config.yaml
   ```

1. Create kind cluster:

   ```bash
   ./kind_init.sh
   ```

1. Set up google credentials:

   - This is a JSON file for your google service account. You should have
     permissions to manage secrets and storage objects.

   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=google-creds.json
   ```

1. Update Dockerfiles to copy creds if necessary by adding these two lines:

   ```docker
   COPY ./google-creds.json /google-creds.json
   ENV GOOGLE_APPLICATION_CREDENTIALS /google-creds.json
   ```

1. Set the webapp and cluster cryptography keys:

   ```bash
   cs secrets set DJANGO_SECRET_KEY $(openssl rand -hex 32)
   cs secrets set WEB_CS_CRYPT_KEY $(openssl rand -hex 32)
   cs secrets set CS_CRYPT_KEY $(openssl rand -hex 32)
   ```

1. Build webapp docker image:

   ```bash
   export TAG=vbuild-demo
   cs webapp build --dev  # Uses Dockerfile.dev
   ```

1. Push webapp docker image to kind cluster

   ```
   cs webapp push --use-kind
   ```

1. Generate and apply Kubernetes configuration.

   ```
   cs webapp config -o - --update-db --dev | kubectl apply -f -
   ```

   Check deployment status (after a few seconds this is what you should see.):

   ```
   $ kubectl get pods
   NAME                   READY   STATUS    RESTARTS   AGE
   db-b68ddc659-wc7vn     1/1     Running   0          75s
   web-68dd6445c6-gshpq   1/1     Running   0          75s
   ```

   - (optional) Data migration from another machine/cluster. See block below at the end of this doc.

1. Run migrations

   ```bash
   kubectl exec -t deployments/web -- python manage.py migrate
   ```

1. Check that the login page renders:

   ```bash
   kubectl port-forward deployments/web 8000
   ```

   Now you should be able to view the login page at http://loalhost:8000/users/login/.

1. Time to set up the worker cluster. First build the images:

   ```bash
   cs workers svc build
   ```

1. Push the docker images to the kind cluster:

   ```bash
   cs workers svc push --use-kind
   ```

1. Generate and apply kind configuration:

   ```bash
   cs workers svc config -o - --update-redis | kubectl apply -f -
   ```

   Check the status of the deployment:

   ```
   $ kubectl get pods
   NAME                                READY   STATUS    RESTARTS   AGE
   db-b68ddc659-jggqb                  1/1     Running   0          43m
   outputs-processor-666554498-qhwh9   1/1     Running   0          34s
   redis-master-9fbcd8df5-jhj7x        1/1     Running   0          34s
   scheduler-5cf6b5d47-bf2jl           1/1     Running   0          34s
   web-68dd6445c6-5hk6q                1/1     Running   0          44m
   ```

1. Connect the webapp with the workers cluster. Create a user with the username `comp-api-user` through the login page. Retrieve the users API token with the `csk` tool (`pip install -U cs-kit`):

   Set the api token as an environment variable. C/S is transitioning to using a new authentication mechanism for communicating between the cluster and the webapp. For now, we still need this token to make requests to the webapp.

   ```bash
   export CS_API_TOKEN=$(csk --host http://localhost:8000 --username comp-api-user --password password-here --quiet)
   ```

   Open up a shell to the webapp pod:

   ```bash
   kubectl exec -it deployments/web -- python manage.py shell
   ```

   Run these commands to create a cluster for the comp-api-user and register it with the worker cluster that we just set up.

   ```python
   from webapp.apps.users.models import Cluster, Profile
   p = Profile.objects.get(user__username="comp-api-user")
   c = Cluster.objects.create(service_account=p, url="http://scheduler")
   c.create_user_in_cluster("http://web")
   ```

   Approve the user in the workers cluster by running:

   ```bash
   kubectl exec -it deployments/scheduler -- python
   ```

   ```python
   from cs_workers.services.auth import User
   u = User.get("comp-api-user")
   u.approved = True
   u.save()
   ```

   Now the webapp and the compute cluster are connected and it's time to publish an app.

1. Create an app through the publish page: http://localhost:8000/publish/
1. Build, push and deploy the app!

   ```bash
   export TAG=a-model-tag
   # Use the external URL since this is being run from outside the cluster.
   export CS_URL=http://localhost:8000
   cs workers models -n PSLmodels/Tax-Cruncher build
   # Optionally, you can test the app before deploying it:
   # cs workers models -n PSLmodels/Tax-Cruncher test
   cs workers models -n PSLmodels/Tax-Cruncher push --use-kind
   cs workers models -n PSLmodels/Tax-Cruncher config -o - | kubectl apply -f -
   ```

1. Check out the model on the webapp at http://localhost:8000/PSLmodels/Tax-Cruncher/new/

### Migrate data from another cluster/machine.

Redis makes this easy since you can just copy over `redis-data/appendonly.aof` to the `compute-studio` directory and it will be loaded through the Kind volume automatically.

```bash
# create dump on the other machine via:
kubectl exec -t deployments/db -- pg_dumpall -c -U postgres > your-backup.sql

# on current machine
export DB_POD=$(kubectl get pod -l app=db -o jsonpath="{.items[0].metadata.name}")
kubectl cp your-backup.sql $DB_POD:/dump.sql
kubectl exec -it deployments -- /bin/bash
# In Kubernetes pod now...
cat /dump.sql | psql -U postgres
rm /dump.sql
```

You may need to reset the Postgres user password. This can be done from the psql repl via:

```sql
alter user postgres with password 'pg-password-here';
```

You may need to restart the web and db pods to get things synced back up:

```bash
kubectl delete pods $DB_POD
export WEB_POD=$(kubectl get pod -l app=web -o jsonpath="{.items[0].metadata.name}")
kubectl delete pods $WEB_POD
```
