import json
import os
import redis
import uuid
import yaml

from kubernetes import client as kclient, config as kconfig

from cs_workers.utils import clean
from cs_workers.clients.core import Core


redis_conn = dict(
    host=os.environ.get("REDIS_HOST"),
    port=os.environ.get("REDIS_PORT"),
    db=os.environ.get("REDIS_DB"),
    username="scheduler",
    password=os.environ.get("REDIS_SCHEDULER_PW"),
)


class Job(Core):
    def __init__(
        self, project, owner, title, tag, job_id=None, job_kwargs=None, quiet=True
    ):
        super().__init__(project, quiet=quiet)
        self.config = {}
        kconfig.load_kube_config()
        self.api_client = kclient.BatchV1Api()
        self.job = self.configure(owner, title, tag, job_id)
        self.save_job_kwargs(self.job_id, job_kwargs)

    def env(self, owner, title, config):
        safeowner = clean(owner)
        safetitle = clean(title)
        envs = [
            kclient.V1EnvVar("OWNER", config["owner"]),
            kclient.V1EnvVar("TITLE", config["title"]),
            kclient.V1EnvVar("SIM_TIME_LIMIT", str(config["sim_time_limit"])),
        ]
        for sec in ["CS_URL", "REDIS_HOST", "REDIS_PORT", "REDIS_EXECUTOR_PW"]:
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

        for secret in self._list_secrets(config):
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
        return envs

    def configure(self, owner, title, tag, job_id=None):
        if job_id is None:
            job_id = "job:" + str(uuid.uuid4())
        else:
            job_id = str(job_id)
            if not str(job_id).startswith("job:"):
                job_id += "job:"

        if (owner, title) not in self.config:
            self.config.update(self.get_config([(owner, title)]))

        config = self.config[(owner, title)]

        safeowner = clean(owner)
        safetitle = clean(title)
        name = f"{safeowner}-{safetitle}"
        job_name = f"{name}-{job_id}"
        container = kclient.V1Container(
            name=job_name,
            image=f"{self.cr}/{self.project}/{safeowner}_{safetitle}_tasks:{tag}",
            command=["csw", "job", "--job-id", job_id, "--route-name", "sim"],
            env=self.env(owner, title, config),
        )
        # Create and configurate a spec section
        template = kclient.V1PodTemplateSpec(
            metadata=kclient.V1ObjectMeta(
                labels={"app": f"{name}-job", "job-id": job_id}
            ),
            spec=kclient.V1PodSpec(
                restart_policy="Never",
                containers=[container],
                node_selector={"component": "model"},
            ),
        )
        # Create the specification of deployment
        spec = kclient.V1JobSpec(template=template, backoff_limit=1)
        # Instantiate the job object
        job = kclient.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=kclient.V1ObjectMeta(name=job_name),
            spec=spec,
        )

        if not self.quiet:
            print(yaml.dump(job.to_dict()))

        return job

    def save_job_kwargs(self, job_id, job_kwargs):
        with redis.Redis(**redis_conn) as rclient:
            rclient.set(job_id, json.dumps(job_kwargs))

    def create(self):
        return self.api_client.create_namespaced_job(body=self.job, namespace="default")

    def delete(self):
        return self.api_client.delete_namespaced_job(
            name=self.job.metadata.name,
            namespace="default",
            body=kclient.V1DeleteOptions(),
        )

    @property
    def job_id(self):
        if self.job:
            return self.job.spec.template.metadata.labels["job-id"]
        else:
            None
