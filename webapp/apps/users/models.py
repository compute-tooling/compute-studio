from collections import defaultdict
import json

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

from webapp.apps.billing.models import create_billing_objects
from webapp.apps.comp import actions
from webapp.apps.comp.compute import SyncCompute, SyncProjects
from webapp.apps.comp.models import Inputs, ANON_BEFORE
from webapp.settings import DEBUG, COMPUTE_PRICING


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


class ProjectManager(models.Manager):
    def sync_products(self, projects=None):
        if projects is None:
            projects = self.all()
        for project in projects:
            create_billing_objects(project)

    def sync_projects_with_workers(self, data):
        SyncProjects().submit_job(data)


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


class RunningDeployment(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="running_deployments"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    # Uses max length of django username field.
    name = models.CharField(null=True, max_length=150)
    tag = models.CharField(null=True, max_length=64)


class EmbedApproval(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="embed_approvals"
    )
    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="embed_approvals"
    )
    url = models.CharField(max_length=256)
