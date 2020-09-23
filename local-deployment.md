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

1) Run migrations

   ```bash
   kubectl exec -t deployments/web -- python manage.py migrate
   ```

1) Check that the login page renders:

   ```bash
   kubectl port-forward deployments/web 8000
   ```

   Now you should be able to view the login page at http://loalhost:8000/users/login/.

1) Time to set up the worker cluster. First build the images:

   ```bash
   cs workers svc build
   ```

1) Push the docker images to the kind cluster:

   ```bash
   cs workers svc push --use-kind
   ```

1) Generate and apply kind configuration:

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

1) Finally, let's deploy a model. (Make sure you've created it on the C/S instance first!)
   Run the port-forward command from earlier (`kubectl port-forward deployments/web 8000`), and swap to another terminal tab.

   ```bash
   export TAG=a-model-tag
   cs workers models -n PSLmodels/Tax-Cruncher build
   cs workers models -n PSLmodels/Tax-Cruncher push --use-kind
   cs workers models -n PSLmodels/Tax-Cruncher config -o - | kubectl apply -f -
   ```

1) Check out the model on the webapp at http://localhost:8000/PSLmodels/Tax-Cruncher/new/

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
alter user postgres with passwrod 'pg-password-here';
```

You may need to restart the web and db pods to get things synced back up:

```bash
kubectl delete pods $DB_POD
export WEB_POD=$(kubectl get pod -l app=web -o jsonpath="{.items[0].metadata.name}")
kubectl delete pods $WEB_POD
```
