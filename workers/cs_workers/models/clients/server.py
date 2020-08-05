import json
import os
import redis
import sys
import uuid
import yaml

from kubernetes import client as kclient, config as kconfig

from cs_workers.utils import clean, redis_conn_from_env
from cs_workers.config import ModelConfig

PORT = 8010

redis_conn = dict(
    username="scheduler",
    password=os.environ.get("REDIS_SCHEDULER_PW"),
    **redis_conn_from_env(),
)


class Server:
    def __init__(
        self,
        project,
        owner,
        title,
        tag,
        model_config,
        server_name=None,
        cr="gcr.io",
        incluster=True,
        rclient=None,
        quiet=True,
    ):
        self.project = project
        self.owner = owner
        self.title = title
        self.tag = tag
        self.model_config = model_config
        self.server_name = server_name
        self.cr = cr
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
        self.service, self.deployment = self.configure(owner, title, tag, server_name)

    def env(self, owner, title, config):
        safeowner = clean(owner)
        safetitle = clean(title)
        envs = [
            kclient.V1EnvVar("OWNER", config["owner"]),
            kclient.V1EnvVar("TITLE", config["title"]),
        ]
        for sec in [
            "CS_URL",
            # "REDIS_HOST",
            # "REDIS_PORT",
            # "REDIS_EXECUTOR_PW",
        ]:
            envs.append(
                kclient.V1EnvVar(
                    sec,
                    value_from=kclient.V1EnvVarSource(
                        secret_key_ref=(
                            kclient.V1SecretKeySelector(key=sec, name="worker-secret")
                        )
                    ),
                )
            )

        for secret in self.model_config._list_secrets(config):
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
                name="URL_BASE_PATHNAME",
                value=f"/{safeowner}/{safetitle}/{self.server_name}/",
            )
        )

        return envs

    def configure(self, owner, title, tag, server_name):
        config = self.model_config.projects()[f"{owner}/{title}"]

        safeowner = clean(owner)
        safetitle = clean(title)
        name = f"{safeowner}-{safetitle}"
        full_name = f"{name}-{server_name}"
        container = kclient.V1Container(
            name=name,
            image=f"{self.cr}/{self.project}/{safeowner}_{safetitle}_tasks:{tag}",
            command=["csw", "model-serve", "--server-name", server_name],
            env=self.env(owner, title, config),
            resources=kclient.V1ResourceRequirements(**config["resources"]),
            ports=[kclient.V1ContainerPort(container_port=PORT)],
        )
        # Create and configurate a spec section
        template = kclient.V1PodTemplateSpec(
            metadata=kclient.V1ObjectMeta(
                labels={"app": full_name, "server-name": server_name}
            ),
            spec=kclient.V1PodSpec(
                restart_policy="Always",
                containers=[container],
                node_selector={"component": "model"},
            ),
        )
        # Create the specification of deployment
        spec = kclient.V1DeploymentSpec(
            template=template,
            selector=kclient.V1LabelSelector(match_labels={"app": full_name}),
            replicas=1,
        )
        # Instantiate the job object
        deployment = kclient.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=kclient.V1ObjectMeta(name=full_name),
            spec=spec,
        )

        service = kclient.V1Service(
            api_version="v1",
            kind="Service",
            metadata=kclient.V1ObjectMeta(name=full_name),
            spec=kclient.V1ServiceSpec(
                selector={"app": full_name},
                ports=[kclient.V1ServicePort(port=80, target_port=PORT)],
                type="LoadBalancer",
            ),
        )

        # TODO: Update Viz Ingress here.

        if not self.quiet:
            sys.stdout.write(yaml.dump(deployment.to_dict()))
            sys.stdout.write("---\n")
            sys.stdout.write(yaml.dump(service.to_dict()))

        return service, deployment

    def create(self):

        print(self.service_api_client.list_namespaced_service("default",))
        return (
            self.deployment_api_client.create_namespaced_deployment(
                namespace="default", body=self.deployment
            ),
            self.service_api_client.create_namespaced_service(
                namespace="default", body=self.service
            ),
        )

    def delete(self):
        return (
            self.deployment_api_client.delete_namespaced_deployment(
                namespace="default", name=self.deployment.metadata.name
            ),
            self.service_api_client.delete_namespaced_service(
                namespace="default", name=self.service.metadata.name
            ),
        )

    @property
    def full_name(self):
        safeowner = clean(self.owner)
        safetitle = clean(self.title)
        name = f"{safeowner}-{safetitle}"
        return f"{name}-{self.server_name}"


if __name__ == "__main__":
    s = Server(
        project="cs-workers-dev",
        owner="hdoupe",
        title="ccc-widget",
        tag="hank-test-5",
        model_config=ModelConfig("cs-workers-dev", "https://dev.compute.studio"),
        server_name="dash",
        incluster=False,
        quiet=False,
    )
    res = s.create()

    # breakpoint()
