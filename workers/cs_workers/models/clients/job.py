import json
import os
import redis
import uuid
import yaml

from kubernetes import client as kclient, config as kconfig

from cs_workers.utils import clean, redis_conn_from_env

redis_conn = dict(
    username="scheduler",
    password=os.environ.get("REDIS_SCHEDULER_PW"),
    **redis_conn_from_env(),
)


class Job:
    def __init__(
        self,
        project,
        owner,
        title,
        tag,
        model_config,
        job_id=None,
        job_kwargs=None,
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
        self.api_client = kclient.BatchV1Api()
        self.job = self.configure(owner, title, tag, job_id)
        self.save_job_kwargs(self.job_id, job_kwargs)

    def env(self, owner, title, config):
        safeowner = clean(owner)
        safetitle = clean(title)
        envs = [
            kclient.V1EnvVar("OWNER", config["owner"]),
            kclient.V1EnvVar("TITLE", config["title"]),
            kclient.V1EnvVar("EXP_TASK_TIME", str(config["exp_task_time"])),
        ]
        for sec in [
            "CS_URL",
            "REDIS_HOST",
            "REDIS_PORT",
            "REDIS_EXECUTOR_PW",
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
        return envs

    def configure(self, owner, title, tag, job_id=None):
        if job_id is None:
            job_id = str(uuid.uuid4())
        else:
            job_id = str(job_id)

        config = self.model_config.projects()[f"{owner}/{title}"]

        safeowner = clean(owner)
        safetitle = clean(title)
        name = f"{safeowner}-{safetitle}"
        container = kclient.V1Container(
            name=job_id,
            image=f"{self.cr}/{self.project}/{safeowner}_{safetitle}_tasks:{tag}",
            command=["csw", "job", "--job-id", job_id, "--route-name", "sim"],
            env=self.env(owner, title, config),
            resources=kclient.V1ResourceRequirements(**config["resources"]),
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
        spec = kclient.V1JobSpec(
            template=template, backoff_limit=1, ttl_seconds_after_finished=0
        )
        # Instantiate the job object
        job = kclient.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=kclient.V1ObjectMeta(name=job_id),
            spec=spec,
        )

        if not self.quiet:
            print(yaml.dump(job.to_dict()))

        return job

    def save_job_kwargs(self, job_id, job_kwargs):
        if not job_id.startswith("job-"):
            job_id = f"job-{job_id}"
        self.rclient.set(job_id, json.dumps(job_kwargs))

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
