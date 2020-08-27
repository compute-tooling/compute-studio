from collections import defaultdict
import json

from hashids import Hashids
import markdown
import requests

from django.db import models
from django.db.models.functions import TruncMonth
from django.db.models import F, Case, When, Sum, Max
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from django.urls import reverse
from django.contrib.postgres.fields import ArrayField, JSONField
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.http import Http404

from webapp.apps.billing.models import create_billing_objects
from webapp.apps.comp import actions
from webapp.apps.comp.compute import SyncCompute, SyncProjects, WORKER_HN
from webapp.apps.comp.models import Inputs, ANON_BEFORE
from webapp.settings import DEBUG, COMPUTE_PRICING


hashids = Hashids(
    "cs-salt", min_length=6, alphabet="abcdefghijklmnopqrstuvwxyz1234567890"
)


def is_profile_active(user):
    if getattr(user, "profile", False):
        return user.profile.is_active
    return False


def create_profile_from_user(user):
    Profile.objects.create(user=user, is_active=True)
    email_msg = EmailMessage(
        subject="Welcome to Compute Studio!",
        body=(
            f"Hello {user.username}, welcome to Compute Studio. "
            f"Please write back here if you have any "
            f"questions or there is anything else we "
            f"can do to help you get up and running."
        ),
        from_email="Hank Doupe <hank@compute.studio>",
        to=[user.email],
        bcc=["matt.h.jensen@gmail.com", "hank@compute.studio"],
    )
    try:
        email_msg.send(fail_silently=True)
    except Exception as e:
        print(e)
        if not DEBUG:
            raise e


class User(AbstractUser):
    def __str__(self):
        return self.email


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=False)

    def recent_models(self, limit):
        return [
            Project.objects.get(pk=project["project"])
            for project in self.sims.values("project")
            .annotate(recent_date=Max("creation_date"))
            .order_by("-recent_date")[:limit]
        ]

    def costs_breakdown(self, projects=None):
        if projects is None:
            projects = Project.objects.all()
        agg = defaultdict(float)
        for project in projects:
            sims = (
                self.sims.filter(sponsor=self) | self.sims.filter(sponsor__isnull=True)
            ).filter(project=project)
            res = (
                sims.values(month=TruncMonth("creation_date"))
                .annotate(
                    effective=Case(When(run_cost=0.0, then=0.01), default=F("run_cost"))
                )
                .annotate(Sum("effective"))
            )
            for month in res:
                agg[month["month"]] += float(month["effective__sum"])
        return {k.strftime("%B %Y"): v for k, v in sorted(agg.items())}

    def can_run(self, project):
        if not self.is_active:
            return False
        if hasattr(self.user, "customer") and self.user.customer:
            return True

        return project.is_sponsored

    @property
    def status(self):
        if not self.is_active:
            return "inactive"
        if hasattr(self, "customer"):
            return "customer"
        else:
            return "profile"

    def __str__(self):
        return self.user.username

    class Meta:
        # not in use yet...
        permissions = (("access_public", "Has access to public projects"),)


class Cluster(models.Model):
    url = models.URLField(max_length=64)
    access_token = models.CharField(max_length=128, null=True)
    service_account = models.OneToOneField(
        Profile, null=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True)

    def headers(self):
        return {"Authorization": f"Token {self.access_token}"}

    def create_user_in_cluster(self, cs_url):
        resp = requests.post(
            f"{self.url}/auth/",
            json={
                "username": self.service_account.user.username,
                "url": cs_url,
                "email": self.service_account.user.email,
            },
        )
        if resp.status_code == 200:
            self.access_token = resp.json()["token"]
            self.save()
            return self

        raise Exception(f"{resp.status_code} {resp.text}")


class ProjectManager(models.Manager):
    def sync_products(self, projects=None):
        if projects is None:
            projects = self.all()
        for project in projects:
            create_billing_objects(project)

    def sync_project_with_workers(self, project, cluster):
        SyncProjects().submit_job(project, cluster)


class Project(models.Model):
    SECS_IN_HOUR = 3600.0
    title = models.CharField(max_length=255)
    oneliner = models.CharField(max_length=10000)
    description = models.CharField(max_length=10000)
    repo_url = models.URLField()
    repo_tag = models.CharField(default="master", max_length=32)
    owner = models.ForeignKey(
        Profile, null=True, related_name="projects", on_delete=models.CASCADE
    )
    sponsor = models.ForeignKey(
        Profile, null=True, related_name="sponsored_projects", on_delete=models.SET_NULL
    )
    sponsor_message = models.CharField(null=True, blank=True, max_length=10000)
    pay_per_sim = models.BooleanField(default=True)
    is_public = models.BooleanField(default=True)

    cluster = models.ForeignKey(
        Cluster, null=True, related_name="projects", on_delete=models.SET_NULL
    )

    tech = models.CharField(
        choices=(
            ("python-paramtools", "Python-ParamTools"),
            ("dash", "Dash"),
            ("bokeh", "Bokeh"),
        ),
        default="python-paramtools",
        max_length=64,
    )

    callable_name = models.CharField(null=True, max_length=128)

    status = models.CharField(
        choices=(
            ("live", "live"),
            ("updating", "updating"),
            ("pending", "pending"),
            ("staging", "staging"),
            ("requires fixes", "requires fixes"),
        ),
        default="live",
        max_length=32,
    )

    # ram, vcpus
    def callabledefault():
        return [4, 2]

    cpu = models.DecimalField(max_digits=5, decimal_places=1, null=True, default=2)
    memory = models.DecimalField(max_digits=5, decimal_places=1, null=True, default=6)

    exp_task_time = models.IntegerField(null=True)
    exp_num_tasks = models.IntegerField(null=True)

    # permission type of the model
    permission_type = models.CharField(
        choices=(("default", "default"), ("sponsored", "sponsored")),
        default="default",
        max_length=32,
    )

    listed = models.BooleanField(default=True)

    cluster_type = models.CharField(default="single-core", max_length=32)

    latest_tag = models.CharField(null=True, max_length=64)
    staging_tag = models.CharField(null=True, max_length=64)

    objects = ProjectManager()

    def __str__(self):
        return f"{self.owner}/{self.title}"

    @staticmethod
    def get_or_none(**kwargs):
        try:
            res = Project.objects.get(**kwargs)
        except Project.DoesNotExist:
            res = None
        return res

    def exp_job_info(self, adjust=False):
        rate_per_sec = self.server_cost / 3600
        job_time = self.exp_task_time * (self.exp_num_tasks or 1)
        cost = round(rate_per_sec * job_time, 4)
        if adjust:
            return max(cost, 0.01), job_time
        else:
            return cost, job_time

    def run_cost(self, run_time, adjust=False):
        """
        Calculate the cost of a project run. The run time is scaled by the time
        required for it to cost one penny. If adjust is true and the cost is
        less than one penny, then it is rounded up to a penny.
        """
        cost = round(run_time / self.n_secs_per_penny) / 100
        if adjust:
            return max(cost, 0.01)
        else:
            return cost

    @property
    def n_secs_per_penny(self):
        """
        Calculate the number of seconds a project sim needs to run such that
        the cost of that run is one penny.
        """
        return 0.01 / self.server_cost_in_secs

    @property
    def server_cost(self):
        """Hourly compute costs"""
        cpu_price = COMPUTE_PRICING["cpu"]
        memory_price = COMPUTE_PRICING["memory"]
        return float(self.cpu) * cpu_price + float(self.memory) * memory_price

    @property
    def server_cost_in_secs(self):
        """
        Convert server cost from $P/hr to $P/sec.
        """
        return float(self.server_cost) / self.SECS_IN_HOUR

    @staticmethod
    def dollar_to_penny(c):
        return int(round(c * 100, 0))

    @property
    def app_url(self):
        return reverse(
            "app", kwargs={"title": self.title, "username": self.owner.user.username}
        )

    def worker_ext(self, action):
        return f"{self.owner.user.username}/{self.title}/{action}"

    @property
    def is_sponsored(self):
        return self.sponsor is not None

    @property
    def display_sponsor(self):
        if self.sponsor is not None:
            return self.sponsor.user.username
        else:
            return "Not sponsored"

    @property
    def number_runs(self):
        return Inputs.objects.filter(project=self).count()

    @property
    def safe_description(self):
        return mark_safe(markdown.markdown(self.description, extensions=["tables"]))

    def sim_count(self):
        return self.sims.count()

    def user_count(self):
        return self.sims.distinct("owner__user").count()

    @cached_property
    def version(self):
        if self.status not in ("updating", "live"):
            return None
        try:
            success, result = SyncCompute().submit_job(
                project=self, task_name=actions.VERSION, task_kwargs=dict()
            )
            if success:
                return result["version"]
            else:
                print(f"error retrieving version for {self}", result)
                return None
        except Exception as e:
            print(f"error retrieving version for {self}", e)
            import traceback

            traceback.print_exc()
            return None

    def has_write_access(self, user):
        return bool(
            user
            and user.is_authenticated
            and (self.owner.user == user or user.has_perm("write_project", self))
        )

    class Meta:
        permissions = (("write_project", "Write project"),)


class DeploymentException(Exception):
    pass


class DeploymentManager(models.Manager):
    def get_or_create_deployment(self, project, name, owner=None, embed_approval=None):
        if project.sponsor is not None:
            owner = project.sponsor
        if owner is None and embed_approval is None:
            raise DeploymentException("There is no one to bill for this deployment.")
        deployment, created = Deployment.objects.get_or_create(
            project=project,
            name=name,
            deleted_at__isnull=True,
            defaults=dict(owner=owner, embed_approval=embed_approval),
        )
        if created:
            deployment.create_deployment()
        else:
            deployment.load()

        return deployment, created

    def from_hashid(self, hashid):
        """
        Get deployment object from a hash of its pk. Return None
        if the decode does not resolve to a pk.
        """
        pk = hashids.decode(hashid)
        if not pk:
            return None
        else:
            return self.get(pk=pk[0])

    def get_object_from_hashid_or_404(self, hashid):
        """
        Get deployment object from a hash of its pk and 
        raise 404 exception if it does not exist.
        """
        try:
            obj = self.from_hashid(hashid)
        except Deployment.DoesNotExist:
            raise Http404("Object matching query does not exist")
        if obj:
            return obj
        else:
            raise Http404("Object matching query does not exist")


class Deployment(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="deployments"
    )
    embed_approval = models.ForeignKey(
        "EmbedApproval",
        on_delete=models.SET_NULL,
        related_name="deployments",
        null=True,
    )
    owner = models.ForeignKey(
        Profile, on_delete=models.SET_NULL, related_name="deployments", null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True)
    last_load_at = models.DateTimeField(auto_now_add=True)
    last_ping_at = models.DateTimeField(auto_now_add=True)
    # Uses max length of django username field.
    name = models.CharField(null=True, max_length=150)
    tag = models.CharField(null=True, max_length=64)

    status = models.CharField(
        default="creating",
        max_length=32,
        choices=(
            ("creating", "Creating"),
            ("running", "Running"),
            ("terminated", "Terminated"),
        ),
    )

    objects = DeploymentManager()

    def _refresh_status(self, use_cache=False, save=True):
        if use_cache:
            return self.ready
        ready_stats = self.get_deployment()
        running = (
            ready_stats["deployment"]["ready"]
            # and ready_stats["svc"]["ready"]
            and ready_stats["ingressroute"]["ready"]
        )
        if self.deleted_at is not None:
            self.status = "terminated"
        elif running:
            self.status = "running"
        else:
            self.status = "creating"

        if save:
            self.save()
        return self.status

    def load(self):
        status = self._refresh_status(use_cache=False, save=False)
        self.last_load_at = timezone.now()
        self.last_ping_at = timezone.now()
        self.save()
        return status

    def ping(self):
        status = self._refresh_status(use_cache=False, save=False)
        self.last_ping_at = timezone.now()
        self.save()
        return status

    @property
    def hashed_name(self):
        return f"{self.name}-{self.hashid}"

    @property
    def hashid(self):
        return hashids.encode(self.pk)

    def create_deployment(self):
        if self.tag is None:
            self.tag = self.project.latest_tag
            self.save()

        resp = requests.post(
            f"{self.project.cluster.url}/deployments/{self.project}/",
            json={"deployment_name": self.hashed_name, "tag": self.tag,},
            headers=self.project.cluster.headers(),
        )

        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 400:
            data = resp.json()
            if data.get("errors") == ["Deployment is already running"]:
                return self.get_deployment()

        raise Exception(f"{resp.status_code} {resp.text}")

    def get_deployment(self):
        resp = requests.get(
            f"{self.project.cluster.url}/deployments/{self.project}/{self.hashed_name}/",
            headers=self.project.cluster.headers(),
        )
        assert resp.status_code == 200, f"Got {resp.status_code}, {resp.text}"
        return resp.json()

    def delete_deployment(self):
        resp = requests.delete(
            f"{self.project.cluster.url}/deployments/{self.project}/{self.hashed_name}/",
            headers=self.project.cluster.headers(),
        )
        assert resp.status_code == 200, f"Got {resp.status_code}, {resp.text}"
        self.deleted_at = timezone.now()
        self.status = "terminated"
        self.save()
        return resp.json()

    def delete(self, *args, **kwargs):
        self.delete_deployment()
        return super().delete()


class EmbedApproval(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="embed_approvals"
    )
    owner = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="embed_approvals"
    )
    url = models.CharField(max_length=256)
    name = models.CharField(max_length=32, null=False)

    def get_absolute_url(self):
        kwargs = {
            "username": self.project.owner.user.username,
            "title": self.project.title,
            "ea_name": self.name,
        }
        return reverse("embed", kwargs=kwargs)
