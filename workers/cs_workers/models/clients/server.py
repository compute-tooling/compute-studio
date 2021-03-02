import os
import redis
import sys
import yaml

from kubernetes import client as kclient, config as kconfig


from cs_workers.utils import clean, redis_conn_from_env
from cs_workers.config import ModelConfig
from cs_workers.ingressroute import IngressRouteApi, ingressroute_template
from cs_workers.models.secrets import ModelSecrets

PORT = 8010

redis_conn = dict(
    username="scheduler",
    password=os.environ.get("REDIS_SCHEDULER_PW"),
    **redis_conn_from_env(),
)

VIZ_HOST = os.environ.get("VIZ_HOST", "viz.compute.studio")


class Server:
    def __init__(
        self,
        project,
        owner,
        title,
        tag,
        model_config,
        callable_name,
        deployment_name="default",
        namespace="default",
        cr="gcr.io",
        viz_host=VIZ_HOST,
        incluster=True,
        rclient=None,
        quiet=True,
    ):
        self.project = project
        self.owner = owner
        self.title = title
        self.tag = tag
        self.model_config = model_config
        self.callable_name = callable_name
        self.deployment_name = deployment_name
        self.namespace = namespace
        self.cr = cr
        self.viz_host = viz_host
        self.quiet = quiet

        self.incluster = incluster
        if rclient is None:
            self.rclient = redis.Redis(**redis_conn)
        else:
            self.rclient = rclient
        if self.incluster:
            kconfig.load_incluster_config()
        else:
            kconfig.load_kube_config()
        self.deployment_api_client = kclient.AppsV1Api()
        self.service_api_client = kclient.CoreV1Api()
        self.ir_api_client = IngressRouteApi()

    def env(self, owner, title, deployment_name, config):
        safeowner = clean(owner)
        safetitle = clean(title)
        envs = [
            kclient.V1EnvVar("OWNER", config["owner"]),
            kclient.V1EnvVar("TITLE", config["title"]),
        ]

        for secret in ModelSecrets(
            owner=owner, title=title, project=self.project
        ).list():
            envs.append(
                kclient.V1EnvVar(
                    name=secret,
                    value_from=kclient.V1EnvVarSource(
                        secret_key_ref=(
                            kclient.V1SecretKeySelector(
                                key=secret, name=f"{safeowner}-{safetitle}-secret"
                            )
                        )
                    ),
                )
            )

        envs.append(
            kclient.V1EnvVar(
                name="URL_BASE_PATHNAME", value=f"/{owner}/{title}/{deployment_name}/",
            )
        )

        return envs

    def configure(self):
        config = self.model_config
        safeowner = clean(self.owner)
        safetitle = clean(self.title)
        app_name = f"{safeowner}-{safetitle}"
        name = f"{app_name}-{self.deployment_name}"

        if config["tech"] == "dash":
            app_module = config.get("app_location", None) or "cs_config.functions"
            cmd = ["gunicorn", f"{app_module}:{self.callable_name}"]
        elif config["tech"] == "bokeh":
            cmd = [
                "bokeh",
                "serve",
                config["app_location"],
                "--address",
                "0.0.0.0",
                "--port",
                str(PORT),
                "--prefix",
                f"/{self.owner}/{self.title}/{self.deployment_name}/",
                f"--allow-websocket-origin={self.viz_host}",
            ]
        else:
            raise ValueError(
                f"Unknown tech: {config['tech']}. Must be one of: bokeh, dash."
            )

        print("got config", config)
        print("running cmd", cmd)

        container = kclient.V1Container(
            name=name,
            image=f"{self.cr}/{self.project}/{safeowner}_{safetitle}_tasks:{self.tag}",
            command=cmd,
            env=self.env(self.owner, self.title, self.deployment_name, config),
            resources=kclient.V1ResourceRequirements(**config["resources"]),
            ports=[kclient.V1ContainerPort(container_port=PORT)],
        )
        # Create and configurate a spec section
        template = kclient.V1PodTemplateSpec(
            metadata=kclient.V1ObjectMeta(labels={"app": name}),
            spec=kclient.V1PodSpec(
                restart_policy="Always",
                containers=[container],
                node_selector={"component": "model"},
            ),
        )
        # Create the specification of deployment
        spec = kclient.V1DeploymentSpec(
            template=template,
            selector=kclient.V1LabelSelector(match_labels={"app": name}),
            replicas=1,
        )
        # Instantiate the deployment object
        deployment = kclient.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=kclient.V1ObjectMeta(name=name),
            spec=spec,
        )

        service = kclient.V1Service(
            api_version="v1",
            kind="Service",
            metadata=kclient.V1ObjectMeta(name=name),
            spec=kclient.V1ServiceSpec(
                selector={"app": name},
                ports=[
                    kclient.V1ServicePort(port=80, target_port=PORT, protocol="TCP")
                ],
                type="LoadBalancer",
            ),
        )

        path_prefix = f"/{self.owner}/{self.title}/{self.deployment_name}"
        routes = [
            {
                "kind": "Rule",
                "match": f"Host(`{self.viz_host}`) && PathPrefix(`{path_prefix}`)",
                "services": [{"name": name, "port": 80}],
            }
        ]
        ingressroute = ingressroute_template(
            namespace=self.namespace, name=name, routes=routes, tls=True
        )

        if not self.quiet:
            sys.stdout.write(yaml.dump(deployment.to_dict()))
            sys.stdout.write("---\n")
            sys.stdout.write(yaml.dump(service.to_dict()))

        self.service, self.deployment, self.ingressroute = (
            service,
            deployment,
            ingressroute,
        )

    def deployment_from_cluster(self):
        try:
            return self.deployment_api_client.read_namespaced_deployment(
                self.full_name, self.namespace
            )
        except kclient.rest.ApiException as e:
            if e.reason != "Not Found":
                raise e
        return None

    def service_from_cluster(self):
        try:
            return self.service_api_client.read_namespaced_service(
                self.full_name, self.namespace
            )
        except kclient.rest.ApiException as e:
            if e.reason != "Not Found":
                raise e
        return None

    def ingressroute_from_cluster(self):
        try:
            return self.ir_api_client.get_namespaced_ingressroute(
                self.full_name, self.namespace
            )
        except kclient.rest.ApiException as e:
            if e.reason != "Not Found":
                raise e
        return None

    def ready_stats(self):
        deployment = self.deployment_from_cluster()
        if deployment is not None:
            dep_ready = {
                "ready": (deployment.status.ready_replicas or 0) > 0,
                "created_at": str(deployment.metadata.creation_timestamp),
            }
        else:
            dep_ready = {"ready": False, "created_at": None}

        svc = self.service_from_cluster()
        if (
            svc
            and svc.status.load_balancer.ingress is not None
            and len(svc.status.load_balancer.ingress)
            and svc.status.load_balancer.ingress[0].ip is not None
        ):
            svc_ready = {
                "ready": True,
                "created_at": str(svc.metadata.creation_timestamp),
            }
        elif svc:
            svc_ready = {
                "ready": False,
                "created_at": str(svc.metadata.creation_timestamp),
            }
        else:
            svc_ready = {"ready": False, "created_at": None}

        # IR will be ready just about immediately.
        ir = self.ingressroute_from_cluster()
        if ir is not None:
            ir_ready = {
                "ready": True,
                "created_at": ir["metadata"]["creationTimestamp"],
            }
        else:
            ir_ready = {"ready": False, "created_at": None}

        return {
            "deployment": dep_ready,
            "svc": svc_ready,
            "ingressroute": ir_ready,
        }

    def create(self):
        deployment_resp = self.deployment_api_client.create_namespaced_deployment(
            namespace=self.namespace, body=self.deployment
        )

        service_resp = self.service_api_client.create_namespaced_service(
            namespace=self.namespace, body=self.service
        )

        ingressroute_resp = self.ir_api_client.create_namespaced_ingressroute(
            namespace=self.namespace, body=self.ingressroute
        )

        return deployment_resp, service_resp, ingressroute_resp

    def delete(self):
        deleted = {
            "deployment": {"deleted": False},
            "svc": {"deleted": False},
            "ingressroute": {"deleted": False},
        }
        if self.deployment_from_cluster():
            print(f"deleting deployment: {self.full_name}")
            self.deployment_api_client.delete_namespaced_deployment(
                namespace=self.namespace, name=self.full_name
            )
            deleted["deployment"] = {"deleted": True}
        else:
            print(f"deployment not found: {self.full_name}")

        if self.service_from_cluster():
            print(f"deleting service: {self.full_name}")
            self.service_api_client.delete_namespaced_service(
                namespace=self.namespace, name=self.full_name
            )
            deleted["svc"] = {"deleted": True}
        else:
            print(f"service not found: {self.full_name}")

        if self.ingressroute_from_cluster():
            print(f"deleting ingressroute: {self.full_name}")
            self.ir_api_client.delete_namespaced_ingressroute(
                name=self.full_name, namespace=self.namespace
            )
            deleted["ingressroute"] = {"deleted": True}
        else:
            print(f"ingressroute not found: {self.full_name}")

        return deleted

    @property
    def full_name(self):
        safeowner = clean(self.owner)
        safetitle = clean(self.title)
        return f"{safeowner}-{safetitle}-{self.deployment_name}"
