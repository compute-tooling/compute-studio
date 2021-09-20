from collections import defaultdict
from datetime import timedelta, datetime
import json
import secrets
import uuid

import markdown
import requests

from django.db import models, transaction
from django.db.models.functions import TruncMonth
from django.db.models import F, Case, When, Sum, Max, Q, Count
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from django.urls import reverse
from django.contrib.postgres.fields import ArrayField, JSONField
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.http import Http404

from guardian.shortcuts import (
    assign_perm,
    remove_perm,
    get_perms,
    get_users_with_perms,
    get_objects_for_user,
)

from webapp.apps.comp import actions
from webapp.apps.comp.compute import SyncCompute, SyncProjects
from webapp.apps.comp.models import Inputs, ANON_BEFORE
from webapp.settings import (
    DEBUG,
    COMPUTE_PRICING,
    DEFAULT_CLUSTER_USER,
    HAS_USAGE_RESTRICTIONS,
    FREE_PRIVATE_SIMS,
    FREE_PRIVATE_SIMS_START_DATE,
)

from webapp.apps.users.exceptions import PrivateAppException

import cs_crypt
import jwt

try:
    cryptkeeper = cs_crypt.CryptKeeper()
except cs_crypt.EncryptionUnavailable:
    import warnings

    warnings.warn("Encryption unavailable.")

    cryptkeeper = None


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
    objects: models.Manager
    sims: models.QuerySet
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=False)

    def remaining_private_sims(self, project=None):
        """Calculate number of remaining private simulations for user on free tier."""
        thirty_days_ago = timezone.now() - timedelta(days=30)
        if thirty_days_ago < FREE_PRIVATE_SIMS_START_DATE:
            thirty_days_ago = FREE_PRIVATE_SIMS_START_DATE

        def remaining(c):
            return max(FREE_PRIVATE_SIMS - c, 0)

        kwargs = dict(
            sims__owner=self,
            sims__is_public=False,
            sims__creation_date__gte=thirty_days_ago,
        )
        if project is not None:
            kwargs["sims__project"] = project

        private_count = Count("sims", filter=Q(**kwargs))
        res = Project.objects.annotate(private_count=private_count).filter(
            private_count__gt=0
        )
        private_sims = {
            str(project).lower(): remaining(project.private_count) for project in res
        }

        return private_sims

    def recent_models(self, limit):
        return [
            Project.objects.get(pk=project["project"])
            for project in self.sims.values("project")
            .annotate(recent_date=Max("creation_date"))
            .order_by("-recent_date")[:limit]
            if project["project"] is not None
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
        if (
            hasattr(self.user, "customer")
            and self.user.customer.card_info() is not None
        ):
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


class ClusterManager(models.Manager):
    def default(self):
        return self.get(service_account__user__username=DEFAULT_CLUSTER_USER)


class ClusterLoginException(Exception):
    pass


class Cluster(models.Model):
    url = models.URLField(max_length=64)
    service_account = models.OneToOneField(
        Profile, null=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True)

    # v0
    jwt_secret = models.CharField(max_length=512, null=True)

    # v1
    cluster_password = models.CharField(max_length=512, null=True)
    access_token = models.CharField(max_length=512, null=True)
    access_token_expires_at = models.DateTimeField(null=True)

    # Make viz host configurable to work with multiple clusters at once.
    viz_host = models.CharField(max_length=128, null=True)

    version = models.CharField(null=False, max_length=32)

    objects = ClusterManager()

    def ensure_access_token(self):
        missing_token = self.access_token is None
        is_expired = (
            self.access_token_expires_at is None
            or self.access_token_expires_at < (timezone.now() - timedelta(seconds=60))
        )
        print("token is missing", missing_token, "token is expired", is_expired)
        if missing_token or is_expired:
            resp = requests.post(
                f"{self.url}/api/v1/login/access-token",
                data={
                    "username": str(self.service_account),
                    "password": self.cluster_password,
                },
            )
            if resp.status_code != 200:
                raise ClusterLoginException(
                    f"Expected 200, got {resp.status_code}: {resp.text}"
                )
            data = resp.json()
            self.access_token = data["access_token"]
            self.access_token_expires_at = datetime.fromisoformat(data["expires_at"])
            self.save()
            self.refresh_from_db()

    def headers(self):
        if self.version == "v0":
            jwt_token = jwt.encode(
                {"username": self.service_account.user.username,},
                cryptkeeper.decrypt(self.jwt_secret),
            )
            return {
                "Authorization": jwt_token,
                "Cluster-User": self.service_account.user.username,
            }
        elif self.version == "v1":
            self.ensure_access_token()
            return {"Authorization": f"Bearer {self.access_token}"}

    def create_user_in_cluster(self, cs_url):
        # only works for v0.
        resp = requests.post(
            f"{self.url}/auth/",
            json={
                "username": self.service_account.user.username,
                "url": cs_url,
                "email": self.service_account.user.email,
            },
        )
        if resp.status_code == 200:
            self.jwt_secret = cryptkeeper.encrypt(resp.json()["jwt_secret"])
            self.save()
            return self

        raise Exception(f"{resp.status_code} {resp.text}")

    @property
    def path_prefix(self):
        if self.version == "v0":
            return ""
        else:
            return "/api/v1"


class ProjectPermissions:
    READ = (
        "read_project",
        "Users with this permission may view and run this project, even if it's private.",
    )
    WRITE = (
        "write_project",
        "Users with this permission may edit the project and view its usage statistics.",
    )
    ADMIN = (
        "admin_project",
        "Users with this permission control the visibility of this project and who has read, write, and admin access to it.",
    )


def get_project_or_404(queryset, user=None, raise_http404=True, **kwargs):
    try:
        if user is None:
            return queryset.objects.get(is_public=True, **kwargs)

        user_has_perms = get_objects_for_user(
            user,
            perms=["read_project", "write_project", "admin_project"],
            klass=queryset,
            any_perm=True,
        )

        return queryset.get(Q(is_public=True) | Q(pk__in=user_has_perms), **kwargs)

    except Project.DoesNotExist as dne:
        if raise_http404:
            raise Http404()
        else:
            raise dne


def projects_with_perms(user, queryset=None):
    if queryset is None:
        queryset = Project.objects.all()
    return get_objects_for_user(
        user,
        perms=["read_project", "write_project", "admin_project"],
        klass=queryset,
        any_perm=True,
    )


def projects_with_access(user, queryset=None):
    if queryset is None:
        queryset = Project.objects.all()
    return queryset.filter(
        Q(is_public=True) | Q(pk__in=projects_with_perms(user, queryset))
    )


class ProjectManager(models.Manager):
    def sync_project_with_workers(self, project, cluster):
        SyncProjects().submit_job(project, cluster)

    @transaction.atomic
    def create(self, *args, **kwargs):
        project = super().create(*args, **kwargs)
        if project.cluster is None:
            project.cluster = Cluster.objects.default()
        if not project.is_public:
            project.make_private_test()
        project.assign_role("admin", project.owner.user)
        project.assign_role("write", project.cluster.service_account.user)
        return project


def get_server_cost(cpu, memory):
    """Hourly compute costs"""
    cpu_price = COMPUTE_PRICING["cpu"]
    memory_price = COMPUTE_PRICING["memory"]
    return float(cpu) * cpu_price + float(memory) * memory_price


class Project(models.Model):
    READ = ProjectPermissions.READ
    WRITE = ProjectPermissions.WRITE
    ADMIN = ProjectPermissions.ADMIN

    SECS_IN_HOUR = 3600.0

    title = models.CharField(max_length=255)
    oneliner = models.CharField(max_length=10000)
    description = models.CharField(max_length=10000)
    social_image_link = models.URLField(null=True)
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
            ("streamlit", "Streamlit"),
        ),
        max_length=64,
        null=True,
    )

    callable_name = models.CharField(null=True, max_length=128)
    app_location = models.CharField(null=True, max_length=256)

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

    latest_tag = models.ForeignKey(
        "Tag", null=True, on_delete=models.SET_NULL, related_name="latest"
    )
    staging_tag = models.ForeignKey(
        "Tag", null=True, on_delete=models.SET_NULL, related_name="staging"
    )

    embed_background_color = models.CharField(default="white", max_length=128)

    objects = ProjectManager()

    use_iframe_resizer = models.BooleanField(default=True, null=True, blank=True)

    def __str__(self):
        return f"{self.owner}/{self.title}"

    @staticmethod
    def get_or_none(**kwargs):
        try:
            res = Project.objects.get(**kwargs)
        except Project.DoesNotExist:
            res = None
        return res

    @property
    def status(self):
        if self.latest_tag is not None:
            return "running"
        elif self.repo_url:
            return "staging"
        elif (
            self.tech is not None and not self.callable_name and not self.exp_task_time
        ):
            return "configuring"
        elif not self.repo_url:
            return "installing"
        else:
            return "created"

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
        return get_server_cost(self.cpu, self.memory)

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
        if self.tech != "python-paramtools":
            return None
        if self.status != "running":
            return None
        if self.latest_tag:
            return self.latest_tag.version
        if self.staging_tag:
            return self.staging_tag.version

    def is_owner(self, user):
        return user == self.owner.user

    def make_private_test(self):
        """
        Test if user's plan allows them to make the app private.
        """
        if not HAS_USAGE_RESTRICTIONS:
            return

        user = self.owner.user
        customer = getattr(user, "customer", None)
        if customer is None:
            plan = "free"
        else:
            plan = customer.current_plan()["name"]

        if plan == "free":
            raise PrivateAppException()

    def add_collaborator_test(self):
        """
        Test if user's plan allows them to add a collaborator.
        """
        if not HAS_USAGE_RESTRICTIONS or self.is_public:
            return

        user = self.owner.user
        customer = getattr(user, "customer", None)
        if customer is None:
            plan = "free"
        else:
            plan = customer.current_plan()["name"]

        if plan == "free":
            permission_objects = get_users_with_perms(self)
            num_collaborators = permission_objects.count() - 1
            if num_collaborators > 0:
                raise PrivateAppException()

    """
    The methods below are used for checking if a user has read, write, or admin
    access to a specific project. Users can only have one of these permissions
    at a time, but users with a higher level permission inherit the read/write
    access from the lower level permissions, too.

    This is similar to the permissions system used on the Simulation table. At
    some point these implementations may be abstracted.
    """

    def has_admin_access(self, user):
        if not user or not user.is_authenticated:
            return False

        return user.has_perm(Project.ADMIN[0], self)

    def has_write_access(self, user):
        if not user or not user.is_authenticated:
            return False

        return user.has_perm(Project.WRITE[0], self) or self.has_admin_access(user)

    def has_read_access(self, user):
        # Everyone has access to this sim.
        if self.is_public:
            return True

        if not user or not user.is_authenticated:
            return False
        return user.has_perm(Project.READ[0], self) or self.has_write_access(user)

    def remove_permissions(self, user):
        for permission in get_perms(user, self):
            remove_perm(permission, user, self)

    def grant_admin_permissions(self, user):
        self.remove_permissions(user)
        self.add_collaborator_test()
        assign_perm(Project.ADMIN[0], user, self)

    def grant_write_permissions(self, user):
        self.remove_permissions(user)
        self.add_collaborator_test()
        assign_perm(Project.WRITE[0], user, self)

    def grant_read_permissions(self, user):
        self.remove_permissions(user)
        self.add_collaborator_test()
        assign_perm(Project.READ[0], user, self)

    @transaction.atomic
    def assign_role(self, role, user):
        """
        Wrapper for granting and revoking permissions for a user.
        Each of the methods below complete multiple DB transactions
        which can cause some race condition-related bugs.

        Roles: read, write, admin, None (none removes all perms.)
        """
        if role == None:
            self.remove_permissions(user)
        elif role == "read":
            self.grant_read_permissions(user)
        elif role == "write":
            self.grant_write_permissions(user)
        elif role == "admin":
            self.grant_admin_permissions(user)
        else:
            raise ValueError(
                f"Received invalid role: {role}. Choices are read, write, or admin."
            )

    def role(self, user):
        if not user or not user.is_authenticated:
            return None

        perms = get_perms(user, self)
        if not perms:
            return None
        elif perms == [Project.READ[0]]:
            return "read"
        elif perms == [Project.WRITE[0]]:
            return "write"
        elif perms == [Project.ADMIN[0]]:
            return "admin"

    class Meta:
        permissions = (
            ProjectPermissions.READ,
            ProjectPermissions.WRITE,
            ProjectPermissions.ADMIN,
        )


class Build(models.Model):
    objects: models.Manager

    BUILD_STATUSES = (
        ("created", "Created"),
        ("building", "Building"),
        ("testing", "Testing"),
        ("pushing", "Pushing"),
        ("cancelled", "Cancelled"),
        ("success", "Success"),
        ("failure", "Failure"),
    )

    project = models.ForeignKey(
        "Project", on_delete=models.SET_NULL, related_name="builds", null=True
    )
    cluster = models.ForeignKey(
        "Cluster", on_delete=models.SET_NULL, related_name="builds", null=True,
    )
    cluster_build_id = models.IntegerField(null=True)
    created_at = models.DateTimeField(null=True)
    finished_at = models.DateTimeField(null=True)
    cancelled_at = models.DateTimeField(null=True)
    provider_data = JSONField(null=True)
    status = models.CharField(null=True, max_length=32, choices=BUILD_STATUSES,)
    failed_at_stage = models.CharField(
        null=True, max_length=32, choices=BUILD_STATUSES,
    )
    tag = models.OneToOneField(
        "Tag", on_delete=models.SET_NULL, related_name="build", null=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cluster", "cluster_build_id"], name="unique_cluster_build"
            )
        ]

    def start(self):
        cluster: Cluster = self.project.cluster
        resp = requests.post(
            f"{cluster.url}{cluster.path_prefix}/builds/{self.project}/",
            json={},
            headers=cluster.headers(),
        )
        resp.raise_for_status()

        data = resp.json()
        print("data", data)
        self.created_at = data["created_at"]
        # self.status = data["status"]
        self.cluster_build_id = data["id"]
        self.save()
        return data

    def refresh_status(self, force_reload=False):
        cluster: Cluster = self.project.cluster
        if not force_reload and self.status in ("success", "failure"):
            return
        resp = requests.get(
            f"{cluster.url}{cluster.path_prefix}/builds/{self.cluster_build_id}/",
            json={},
            headers=cluster.headers(),
        )
        resp.raise_for_status()
        data = resp.json()

        self.created_at = data["created_at"]
        self.cancelled_at = data["cancelled_at"]
        self.finished_at = data["finished_at"]
        self.failed_at_stage = data.get("failed_at_stage")
        self.status = data["status"]

        # TODO: Store abbreviated version of logs.
        self.provider_data = data["provider_data"]
        self.save()
        return data


class Tag(models.Model):
    objects: models.Manager

    project = models.ForeignKey(
        "Project", on_delete=models.SET_NULL, related_name="tags", null=models.CASCADE
    )
    image_tag = models.CharField(null=True, max_length=64)
    cpu = models.DecimalField(max_digits=5, decimal_places=1, null=True, default=2)
    memory = models.DecimalField(max_digits=5, decimal_places=1, null=True, default=6)
    created_at = models.DateTimeField(auto_now_add=True)
    version = models.CharField(max_length=255, null=True)

    def __str__(self):
        return str(self.image_tag)

    @property
    def server_cost(self):
        """Hourly compute costs"""
        return get_server_cost(self.cpu, self.memory)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "image_tag"], name="unique_project_tag"
            )
        ]


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


def default_short_id():
    return secrets.token_hex(3)


class Deployment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    short_id = models.CharField(max_length=6, default=default_short_id)
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
    tag = models.ForeignKey("Tag", null=True, on_delete=models.SET_NULL)

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
    def public_name(self):
        return f"{self.name}-{self.short_id}"

    def create_deployment(self):
        if self.tag is None:
            self.tag = self.project.latest_tag
            self.save()

        cluster: Cluster = self.project.cluster
        resp = requests.post(
            f"{cluster.url}{cluster.path_prefix}/deployments/{self.project}/",
            json={"deployment_name": self.public_name, "tag": str(self.tag)},
            headers=cluster.headers(),
        )

        if resp.status_code in (200, 201):
            return resp.json()
        elif resp.status_code == 400:
            data = resp.json()
            if data.get("errors") == ["Deployment is already running"]:
                return self.get_deployment()

        raise Exception(f"{resp.status_code} {resp.text}")

    def get_deployment(self):
        cluster: Cluster = self.project.cluster
        resp = requests.get(
            f"{cluster.url}{cluster.path_prefix}/deployments/{self.project}/{self.public_name}/",
            headers=cluster.headers(),
        )
        assert resp.status_code == 200, f"Got {resp.status_code}, {resp.text}"
        return resp.json()

    def delete_deployment(self):
        cluster: Cluster = self.project.cluster
        resp = requests.delete(
            f"{cluster.url}{cluster.path_prefix}/deployments/{self.project}/{self.public_name}/",
            headers=cluster.headers(),
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
